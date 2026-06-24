import { useEffect } from "react";
import { Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { DiscoverScreen } from "./screens/DiscoverScreen";
import { TargetingScreen } from "./screens/TargetingScreen";
import { TrailsScreen } from "./screens/TrailsScreen";
import { TripsScreen } from "./screens/TripsScreen";
import { YouScreen } from "./screens/YouScreen";
import { TrailDetailScreen } from "./screens/TrailDetailScreen";
import { OptimalTimeScreen } from "./screens/OptimalTimeScreen";
import { FunDriveNavScreen } from "./screens/FunDriveNavScreen";
import { BirdIdScreen } from "./screens/BirdIdScreen";
import { useAppState } from "./state/AppState";

/** Legacy /catalog/:id deep links now resolve to the unified trail detail. */
function CatalogRedirect() {
  const { id = "" } = useParams();
  const { setDetailTrailId } = useAppState();
  const navigate = useNavigate();
  useEffect(() => {
    if (id) setDetailTrailId(id);
    navigate("/trail", { replace: true });
  }, [id, setDetailTrailId, navigate]);
  return null;
}

export function App() {
  return (
    <div className="app-shell">
      <Routes>
        {/* Core tabs */}
        <Route path="/" element={<DiscoverScreen />} />
        <Route path="/birbs" element={<TargetingScreen />} />
        <Route path="/trails" element={<TrailsScreen />} />
        <Route path="/trips" element={<TripsScreen />} />
        <Route path="/you" element={<YouScreen />} />
        {/* Flow screens */}
        <Route path="/trail" element={<TrailDetailScreen />} />
        <Route path="/optimal-time" element={<OptimalTimeScreen />} />
        <Route path="/navigate" element={<FunDriveNavScreen />} />
        <Route path="/bird-id" element={<BirdIdScreen />} />
        <Route path="/catalog" element={<Navigate to="/trails" replace />} />
        <Route path="/catalog/:id" element={<CatalogRedirect />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
