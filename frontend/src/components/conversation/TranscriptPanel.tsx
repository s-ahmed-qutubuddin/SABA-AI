import { motion, AnimatePresence } from "framer-motion";
import { useVoiceState } from "../../state/VoiceStateContext";

export function TranscriptPanel() {
  const { turns } = useVoiceState();

  if (turns.length === 0) return null;

  const recent = turns.slice(-4);

  return (
    <div className="mx-auto flex w-full max-w-xl flex-col gap-3">
      <AnimatePresence initial={false}>
        {recent.map((turn) => (
          <motion.div
            key={turn.at}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            className={`glass-card rounded-2xl px-5 py-3.5 shadow-glass ${
              turn.role === "user" ? "self-end" : "self-start"
            }`}
          >
            <div
              className={`mb-1 font-mono text-[10px] tracking-[0.2em] ${
                turn.role === "user" ? "text-text-dim" : "text-signal"
              }`}
            >
              {turn.role === "user" ? "YOU" : "SABA"}
            </div>
            <div className="font-display text-sm leading-relaxed text-text">{turn.text}</div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
