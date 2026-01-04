import { IconMenu, IconCheckCircle, IconXCircle, IconGithub } from "./Icons";

interface NavbarProps {
    connected: boolean;
    onToggleSidebar: () => void;
}

export const Navbar = ({ connected, onToggleSidebar }: NavbarProps) => (
    <nav className="navbar">
        <div className="nav-left">
            <button className="menu-btn mobile-only" onClick={onToggleSidebar}>
                <IconMenu />
            </button>
            <span className="nav-title"> </span>
        </div>
        <div className="nav-right">
            <div className={`status-indicator ${connected ? 'connected' : 'disconnected'}`}>
                {connected ? <IconCheckCircle /> : <IconXCircle />}
                <span>{connected ? "System Online" : "Backend Offline"}</span>
            </div>
            <a href="https://github.com/CagriCatik/Clarion" target="_blank" rel="noreferrer" className="nav-link">
                <IconGithub />
            </a>
        </div>
    </nav>
);
