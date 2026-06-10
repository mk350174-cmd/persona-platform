#!/bin/bash
# Setup Canary Deployment Infrastructure
# Creates ECS canary service, ALB target groups, and CloudWatch alarms

set -e

# Configuration
CLUSTER_NAME="persona-hub-prod"
SERVICE_NAME="persona-hub"
CANARY_SERVICE_NAME="persona-hub-canary"
ALB_NAME="persona-hub-alb"
VPC_ID="${VPC_ID:-vpc-xxxxx}"
SUBNET_IDS="${SUBNET_IDS:-subnet-xxxxx,subnet-yyyyy}"
SECURITY_GROUP_ID="${SECURITY_GROUP_ID:-sg-xxxxx}"

echo "🚀 Setting up canary deployment infrastructure..."

# Step 1: Create canary target group
echo "📋 Creating canary target group..."
CANARY_TG=$(aws elbv2 create-target-group \
  --name persona-hub-canary \
  --protocol HTTP \
  --port 8000 \
  --vpc-id $VPC_ID \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --matcher HttpCode=200 \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

echo "✅ Canary target group created: $CANARY_TG"

# Step 2: Get stable target group ARN
echo "📋 Getting stable target group ARN..."
STABLE_TG=$(aws elbv2 describe-target-groups \
  --names persona-hub-stable \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

echo "✅ Stable target group: $STABLE_TG"

# Step 3: Get ALB ARN
echo "📋 Getting ALB ARN..."
ALB_ARN=$(aws elbv2 describe-load-balancers \
  --names $ALB_NAME \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text)

echo "✅ ALB ARN: $ALB_ARN"

# Step 4: Get listener ARN
echo "📋 Getting ALB listener ARN..."
LISTENER_ARN=$(aws elbv2 describe-listeners \
  --load-balancer-arn $ALB_ARN \
  --query 'Listeners[0].ListenerArn' \
  --output text)

echo "✅ Listener ARN: $LISTENER_ARN"

# Step 5: Create canary ECS service
echo "📋 Creating canary ECS service..."
aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name $CANARY_SERVICE_NAME \
  --task-definition persona-hub \
  --desired-count 2 \
  --load-balancers targetGroupArn=$CANARY_TG,containerName=persona-hub,containerPort=8000 \
  --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_IDS}],securityGroups=[$SECURITY_GROUP_ID],assignPublicIp=DISABLED}" \
  --deployment-configuration maximumPercent=200,minimumHealthyPercent=100 \
  --enable-ecs-managed-tags \
  --tags "key=Type,value=Canary" "key=Environment,value=Production"

echo "✅ Canary ECS service created"

# Step 6: Create ALB rule with weight-based routing
echo "📋 Creating ALB weight-based routing rule..."
aws elbv2 create-rule \
  --listener-arn $LISTENER_ARN \
  --priority 1 \
  --conditions Field=path-pattern,Values="/*" \
  --actions Type=forward,ForwardConfig="{TargetGroups=[{TargetGroupArn=$STABLE_TG,Weight=90},{TargetGroupArn=$CANARY_TG,Weight=10}]}"

echo "✅ ALB rule created (90% stable, 10% canary)"

# Step 7: Create CloudWatch alarms for canary
echo "📋 Creating CloudWatch alarms for canary health..."

# High error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name persona-hub-canary-high-errors \
  --alarm-description "Alert if canary error rate spikes" \
  --metric-name HTTPCode_Target_5XX_Count \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=TargetGroup,Value=targetgroup/persona-hub-canary/abc123 \
  --alarm-actions arn:aws:sns:us-east-1:123456789:persona-hub-alerts

# High latency alarm
aws cloudwatch put-metric-alarm \
  --alarm-name persona-hub-canary-high-latency \
  --alarm-description "Alert if canary latency is high" \
  --metric-name TargetResponseTime \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 300 \
  --threshold 2.0 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=TargetGroup,Value=targetgroup/persona-hub-canary/abc123 \
  --alarm-actions arn:aws:sns:us-east-1:123456789:persona-hub-alerts

echo "✅ CloudWatch alarms created"

# Step 8: Create auto-scaling for canary service
echo "📋 Setting up auto-scaling for canary service..."

aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/$CLUSTER_NAME/$CANARY_SERVICE_NAME \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 5

aws application-autoscaling put-scaling-policy \
  --policy-name $CANARY_SERVICE_NAME-cpu-scaling \
  --service-namespace ecs \
  --resource-id service/$CLUSTER_NAME/$CANARY_SERVICE_NAME \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration file:///dev/stdin << EOF
{
  "TargetValue": 70.0,
  "PredefinedMetricSpecification": {
    "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
  },
  "ScaleOutCooldown": 60,
  "ScaleInCooldown": 300
}
EOF

echo "✅ Auto-scaling configured"

# Step 9: Create CloudWatch dashboard
echo "📋 Creating CloudWatch dashboard..."

aws cloudwatch put-dashboard \
  --dashboard-name PersonaHubCanary \
  --dashboard-body file:///dev/stdin << 'EOF'
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          [ "AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", { "stat": "Sum", "label": "Stable 5xx" } ],
          [ ".", ".", { "stat": "Sum", "label": "Canary 5xx" } ],
          [ ".", "TargetResponseTime", { "stat": "Average", "label": "Stable Latency" } ],
          [ ".", ".", { "stat": "Average", "label": "Canary Latency" } ]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Canary vs Stable Comparison",
        "yAxis": {
          "left": { "min": 0 }
        }
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          [ "AWS/ApplicationELB", "RequestCount", { "stat": "Sum", "label": "Canary Traffic" } ]
        ],
        "period": 60,
        "stat": "Sum",
        "region": "us-east-1",
        "title": "Canary Request Rate"
      }
    }
  ]
}
EOF

echo "✅ CloudWatch dashboard created: PersonaHubCanary"

# Step 10: Store configuration in Secrets Manager for GitHub Actions
echo "📋 Storing configuration in AWS Secrets Manager..."

aws secretsmanager create-secret \
  --name persona-hub/canary-config \
  --description "Canary deployment configuration" \
  --secret-string "{
    \"cluster_name\": \"$CLUSTER_NAME\",
    \"service_name\": \"$SERVICE_NAME\",
    \"canary_service_name\": \"$CANARY_SERVICE_NAME\",
    \"canary_target_group\": \"$CANARY_TG\",
    \"stable_target_group\": \"$STABLE_TG\",
    \"alb_arn\": \"$ALB_ARN\",
    \"listener_arn\": \"$LISTENER_ARN\"
  }" || true

echo "✅ Configuration stored"

# Summary
echo ""
echo "================================"
echo "✅ Canary infrastructure ready!"
echo "================================"
echo ""
echo "📋 Configuration Summary:"
echo "   Cluster: $CLUSTER_NAME"
echo "   Service: $SERVICE_NAME"
echo "   Canary Service: $CANARY_SERVICE_NAME"
echo "   Canary Target Group: $CANARY_TG"
echo "   ALB Rule: 90% stable / 10% canary"
echo ""
echo "🚀 Next steps:"
echo "   1. Update GitHub Actions secrets with:"
echo "      - AWS_ROLE_ARN"
echo "      - ALB_RULE_ARN"
echo ""
echo "   2. Trigger deployment:"
echo "      git push origin main"
echo ""
echo "   3. Watch canary traffic:"
echo "      aws cloudwatch get-dashboard --dashboard-name PersonaHubCanary"
echo ""
