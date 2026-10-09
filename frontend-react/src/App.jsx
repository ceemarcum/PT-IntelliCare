// Routes. HashRouter keeps the same links as before (/app/#/home, /app/#/checkin, ...),
// so FastAPI only has to serve index.html.
import { HashRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppProvider, useApp } from "./lib/AppContext.jsx";
import Layout from "./components/Layout.jsx";
import Login from "./pages/Login.jsx";
import Home from "./pages/Home.jsx";
import Injury from "./pages/Injury.jsx";
import Checkin from "./pages/Checkin.jsx";
import Exercises from "./pages/Exercises.jsx";
import Progress from "./pages/Progress.jsx";
import Insurance from "./pages/Insurance.jsx";

function RequireSignIn({ children }) {
  const { user } = useApp();
  return user ? children : <Navigate to="/login" replace />;
}

function AppRoutes() {
  const { user, landing } = useApp();
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to={landing} replace /> : <Login />} />
      <Route element={<RequireSignIn><Layout /></RequireSignIn>}>
        <Route path="/home" element={<Home />} />
        <Route path="/injury" element={<Injury />} />
        <Route path="/checkin" element={<Checkin />} />
        <Route path="/exercises" element={<Exercises />} />
        <Route path="/progress" element={<Progress />} />
        <Route path="/insurance" element={<Insurance />} />
      </Route>
      <Route path="*" element={<Navigate to={user ? "/home" : "/login"} replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AppProvider>
      <HashRouter>
        <AppRoutes />
      </HashRouter>
    </AppProvider>
  );
}
