import { BrowserRouter, Route, Routes } from "react-router-dom";
import { MotionConfig, motion } from "framer-motion";
import { useState } from "react";
import { AppShell } from "./components/layout/AppShell";
import { SabaOrb } from "./components/orb/SabaOrb";
import { MicControl } from "./components/voice/MicControl";
import { TranscriptPanel } from "./components/conversation/TranscriptPanel";
import { WebResultsPanel } from "./components/web/WebResultsPanel";
import { SystemActionBanner } from "./components/system/SystemActionBanner";
import { useVoiceState } from "./state/VoiceStateContext";
import ConversationsPage from "./pages/ConversationsPage";
import MemoriesPage from "./pages/MemoriesPage";
import NotesPage from "./pages/NotesPage";
import TasksPage from "./pages/TasksPage";
import PreferencesPage from "./pages/PreferencesPage";
import SettingsPage from "./pages/SettingsPage";
import SystemPage from "./pages/SystemPage";
import WebPage from "./pages/WebPage";
import DevicesPage from "./pages/DevicesPage";
import FamilyPage from "./pages/FamilyPage";
import CloudGate from "./CloudGate";

function Home(){
 const {state,turns,systemAction,webResults,connected,sendText}=useVoiceState();
 const latest=turns.length?turns[turns.length-1]:undefined;
 const [text,setText]=useState("");
 const submit=()=>{const value=text.trim();if(!value)return;void sendText(value);setText("");};
 return <div className="command-center">
   <div className="command-grid"/><div className="command-stars"/>
   <header className="hero-header"><div><div className="eyebrow">JAMAL FAMILY ASSISTANT</div><h1>SABA</h1><p><span className="gold-dot"/> Family intelligence · no wake word</p></div>
   <div className="hero-status"><div className="status-chip"><span className={connected?"pulse-dot":"pulse-dot offline"}/> {connected?"CORE LINKED":"CORE OFFLINE"}</div><div className="status-chip">{state==='stopped'?"VOICE DORMANT":"VOICE ARMED"}</div></div></header>
   <div className="command-main">
    <section className="orb-stage glass-royal"><div className="stage-topline"><span>ORCHESTRATION CORE</span><span>{state.toUpperCase()}</span></div><SabaOrb state={state}/><div className="orb-caption"><motion.div key={latest?.text??state} initial={{opacity:0,y:6}} animate={{opacity:1,y:0}} className="live-intent">{latest?.text||"Ready for your next thought."}</motion.div></div><MicControl/></section>
    <aside className="intelligence-rail">
      <div className="glass-royal info-card hero-card"><div className="card-kicker">SABA / PERSONAL AI</div><div className="hero-sentence">Private family intelligence — remembers, acts, and speaks naturally.</div><div className="hero-ai-name">SABA</div><div className="hero-meta"><span>AI ROUTER</span><span>MEMORY</span><span>WEB</span><span>DEVICES</span></div></div>
      <div className="glass-royal info-card"><div className="card-kicker">CURRENT SIGNAL</div><div className="signal-state">{state==='stopped'?"Paused":state==='idle'?"Awaiting intent":state==='listening'?"Listening":state==='thinking'?"Reasoning":state==='speaking'?"Speaking":"Attention required"}</div><div className="signal-line"><span style={{width:state==='listening'?"92%":state==='thinking'?"71%":state==='speaking'?"84%":"31%"}}/></div></div>
      <div className="glass-royal info-card"><div className="card-kicker">ACTIVITY</div><SystemActionBanner action={systemAction}/>{!systemAction&&<div className="muted">No active tool action.</div>}</div>
      <div className="glass-royal info-card"><div className="card-kicker">LATEST SIGNAL</div><div className="recent-turn"><span className="recent-role">{latest?.role??"assistant"}</span><span className="recent-text">{latest?.text??"Talk naturally. Saba is ready."}</span></div></div>
    </aside>
   </div>
   <section className="conversation-dock glass-royal">
     <div className="dock-title"><span>LIVE CHANNEL</span><span>{turns.length?`${turns.length} signals`:"awaiting first signal"}</span></div>
     <div className="chat-compose"><input aria-label="Message Saba" placeholder="Type to Saba…" value={text} onChange={e=>setText(e.target.value)} onKeyDown={e=>{if(e.key==='Enter')submit();}}/><button onClick={submit}>SEND</button></div>
     <TranscriptPanel/><WebResultsPanel results={webResults}/>
   </section>
   <span className="sr-only" role="status" aria-live="polite">{state}</span>
 </div>
}

export default function App(){return <MotionConfig reducedMotion="user"><BrowserRouter><CloudGate><Routes><Route element={<AppShell/>}><Route index element={<Home/>}/><Route path="devices" element={<DevicesPage/>}/><Route path="family" element={<FamilyPage/>}/><Route path="conversations" element={<ConversationsPage/>}/><Route path="memories" element={<MemoriesPage/>}/><Route path="notes" element={<NotesPage/>}/><Route path="tasks" element={<TasksPage/>}/><Route path="preferences" element={<PreferencesPage/>}/><Route path="settings" element={<SettingsPage/>}/><Route path="system" element={<SystemPage/>}/><Route path="web" element={<WebPage/>}/></Route></Routes></CloudGate></BrowserRouter></MotionConfig>}
