import { NavLink } from "react-router-dom";
import {
  Home,
  MessagesSquare,
  Cpu,
  UsersRound,
  Brain,
  StickyNote,
  ListChecks,
  SlidersHorizontal,
  Settings,
  TerminalSquare,
  Globe2,
} from "lucide-react";

const ITEMS = [
  { to: "/", icon: Home, label: "Command", end: true },
  { to: "/devices", icon: Cpu, label: "Devices" },
  { to: "/family", icon: UsersRound, label: "Family" },
  { to: "/conversations", icon: MessagesSquare, label: "Conversations" },
  { to: "/memories", icon: Brain, label: "Memories" },
  { to: "/notes", icon: StickyNote, label: "Notes" },
  { to: "/tasks", icon: ListChecks, label: "Tasks" },
  { to: "/preferences", icon: SlidersHorizontal, label: "Preferences" },
  { to: "/system", icon: TerminalSquare, label: "System" },
  { to: "/web", icon: Globe2, label: "Web Access" },
];

export function IconRail() {
  return (
    <nav className="icon-rail" aria-label="Primary navigation">
      <div className="rail-brand">
        <div className="rail-wordmark">JAMAL</div>
        <div className="rail-sub">FAMILY ASSISTANT</div>
      </div>

      <div className="rail-nav">
        {ITEMS.map(({ to, icon: Icon, label, end }) => (
          <NavLink
            key={label}
            to={to}
            end={end}
            className={({ isActive }) =>
              isActive ? "rail-item rail-item-active" : "rail-item"
            }
          >
            <Icon size={17} strokeWidth={1.7} aria-hidden="true" />
            <span>{label}</span>
          </NavLink>
        ))}
      </div>

      <div className="rail-footer">
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            isActive ? "rail-item rail-item-active" : "rail-item"
          }
        >
          <Settings size={17} strokeWidth={1.7} aria-hidden="true" />
          <span>Settings</span>
        </NavLink>
      </div>
    </nav>
  );
}
