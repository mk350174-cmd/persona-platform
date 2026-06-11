import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Layout from './components/Layout';
import NotificationCenter from './components/NotificationCenter';
import { notificationManager } from './services/notifications';
import Home from './pages/Home';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Catalog from './pages/Catalog';
import PersonaDetail from './pages/PersonaDetail';
import Dashboard from './pages/Dashboard';
import CEIDMonitor from './pages/CEIDMonitor';
import Chat from './pages/Chat';
import Landing from './pages/Landing';
import NotFound from './pages/NotFound';

function PrivateRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">Loading...</div>;
  }

  return isAuthenticated ? children : <Navigate to="/login" />;
}

function App() {
  const { user } = useAuth();

  // Initialize notifications when user is authenticated
  React.useEffect(() => {
    if (user?.id && user?.api_key) {
      notificationManager.init(user.api_key, user.id);
    }

    return () => {
      // Cleanup on unmount
      notificationManager.disconnect();
    };
  }, [user]);

  return (
    <BrowserRouter>
      <NotificationCenter />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />

        <Route element={<Layout />}>
          <Route path="/home" element={<PrivateRoute><Home /></PrivateRoute>} />
          <Route path="/catalog" element={<Catalog />} />
          <Route path="/personas/:id" element={<PersonaDetail />} />
          <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
          <Route path="/ceid-monitor" element={<PrivateRoute><CEIDMonitor /></PrivateRoute>} />
        </Route>

        <Route path="/chat/:id" element={<PrivateRoute><Chat /></PrivateRoute>} />

        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
