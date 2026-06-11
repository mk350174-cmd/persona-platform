import React from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

const COLORS = ['#8b5cf6', '#06b6d4', '#3b82f6', '#f59e0b', '#f97316', '#34d399'];

// Sample data
const dailyMessagesData = [
  { day: 'Mon', messages: 240 },
  { day: 'Tue', messages: 380 },
  { day: 'Wed', messages: 200 },
  { day: 'Thu', messages: 278 },
  { day: 'Fri', messages: 189 },
  { day: 'Sat', messages: 239 },
  { day: 'Sun', messages: 349 },
];

const topPersonasData = [
  { name: 'Socrates', value: 2400, fill: '#8b5cf6' },
  { name: 'Ada Lovelace', value: 1398, fill: '#06b6d4' },
  { name: 'Aristotle', value: 1098, fill: '#3b82f6' },
  { name: 'Marie Curie', value: 908, fill: '#f59e0b' },
  { name: 'Plato', value: 800, fill: '#f97316' },
];

const engagementData = [
  { week: 'Week 1', users: 400, chats: 240 },
  { week: 'Week 2', users: 300, chats: 139 },
  { week: 'Week 3', users: 200, chats: 221 },
  { week: 'Week 4', users: 278, chats: 229 },
];

export default function AnalyticsCharts() {
  return (
    <div className="space-y-8">
      {/* Daily Messages */}
      <div className="glass-panel rounded-xl p-6">
        <h3 className="font-headline-md text-on-surface mb-4">Daily Messages (Last 7 Days)</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={dailyMessagesData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
            <XAxis dataKey="day" stroke="rgba(227, 224, 241, 0.6)" />
            <YAxis stroke="rgba(227, 224, 241, 0.6)" />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(26, 26, 46, 0.8)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '8px',
              }}
            />
            <Bar dataKey="messages" fill="#8b5cf6" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Top Personas */}
      <div className="glass-panel rounded-xl p-6">
        <h3 className="font-headline-md text-on-surface mb-4">Top Personas by Usage</h3>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={topPersonasData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, value }) => `${name}: ${value}`}
              outerRadius={100}
              fill="#8b5cf6"
              dataKey="value"
            >
              {topPersonasData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(26, 26, 46, 0.8)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '8px',
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* User Engagement */}
      <div className="glass-panel rounded-xl p-6">
        <h3 className="font-headline-md text-on-surface mb-4">Active Users & Chats</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={engagementData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
            <XAxis dataKey="week" stroke="rgba(227, 224, 241, 0.6)" />
            <YAxis stroke="rgba(227, 224, 241, 0.6)" />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(26, 26, 46, 0.8)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '8px',
              }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="users"
              stroke="#8b5cf6"
              strokeWidth={2}
              dot={{ fill: '#8b5cf6', r: 5 }}
              activeDot={{ r: 7 }}
            />
            <Line
              type="monotone"
              dataKey="chats"
              stroke="#06b6d4"
              strokeWidth={2}
              dot={{ fill: '#06b6d4', r: 5 }}
              activeDot={{ r: 7 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
