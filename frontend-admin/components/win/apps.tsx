import type { ComponentType } from "react";
import { BarChart3, Play, Server, Cog, Activity, Waves, type LucideIcon } from "lucide-react";
import ForecastRunsApp from "./apps/ForecastRunsApp";
import ForceRunApp from "./apps/ForceRunApp";
import SystemHealthApp from "./apps/SystemHealthApp";
import ServicesApp from "./apps/ServicesApp";
import RuntimeApp from "./apps/RuntimeApp";
import CrossSectionApp from "./apps/CrossSectionApp";

export type AppDef = {
  id: string;
  title: string;
  label: string;
  Icon: LucideIcon;
  color: string;
  /** preferred size as a fraction of the desktop, capped */
  size: { w: number; h: number; maxW: number; maxH: number };
  Component: ComponentType;
};

export const APPS: AppDef[] = [
  { id: "runs", title: "Forecast Runs & Accuracy", label: "Forecast Runs & Accuracy", Icon: BarChart3, color: "#4cc2ff", size: { w: 0.92, h: 0.95, maxW: 1400, maxH: 900 }, Component: ForecastRunsApp },
  { id: "force", title: "Force Forecast Run", label: "Force Forecast Run", Icon: Play, color: "#6ccb5f", size: { w: 0.5, h: 0.85, maxW: 760, maxH: 820 }, Component: ForceRunApp },
  { id: "system", title: "System & Database Health", label: "System & Database Health", Icon: Server, color: "#ffd166", size: { w: 0.6, h: 0.88, maxW: 980, maxH: 860 }, Component: SystemHealthApp },
  { id: "services", title: "Services & Processes", label: "Services & Processes", Icon: Cog, color: "#c8b6ff", size: { w: 0.55, h: 0.6, maxW: 900, maxH: 560 }, Component: ServicesApp },
  { id: "runtime", title: "Runtime & Performance", label: "Runtime & Performance", Icon: Activity, color: "#ff9f6b", size: { w: 0.7, h: 0.92, maxW: 1100, maxH: 900 }, Component: RuntimeApp },
  { id: "xsec", title: "River Cross-Section", label: "River Cross-Section", Icon: Waves, color: "#7fdbda", size: { w: 0.8, h: 0.92, maxW: 1200, maxH: 900 }, Component: CrossSectionApp },
];
