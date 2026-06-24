import { Navigate, Route, Routes } from "react-router-dom";
import { DiscoverScreen } from "./screens/DiscoverScreen";
import { TargetingScreen } from "./screens/TargetingScreen";
import { TrailsScreen } from "./screens/TrailsScreen";
import { TripsScreen } from "./screens/TripsScreen";
import { YouScreen } from "./screens/YouScreen";
import { TrailDetailScreen } from "./screens/TrailDetailScreen";
import { OptimalTimeScreen } from "./screens/OptimalTimeScreen";
import { FunDriveNavScreen } from "./screens/FunDriveNavScreen";
import { BirdIdScreen } from "./screens/BirdIdScreen";
import { CatalogScreen } from "./screens/CatalogScreen";

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
        <Route path="/catalog" element={<CatalogScreen />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
