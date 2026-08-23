import { motion, AnimatePresence } from "framer-motion";
import { Terminal } from "lucide-react";

/**
 * Displays "SYSTEM ACTION \u2014 Opening Safari\u2026" style banners.
 * Prop contract unchanged: `action: string | null`, sourced from
 * VoiceStateContext's `systemAction` field.
 */
export function SystemActionBanner({ action }: { action: string | null }) {
  return (
    <AnimatePresence>
      {action && (
        <motion.div
          initial={{ opacity: 0, y: -10, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -10, scale: 0.98 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="glass-card flex items-center gap-2.5 rounded-full px-4 py-2 font-mono text-xs tracking-[0.12em] text-signal shadow-glow-signal"
        >
          <Terminal size={13} />
          {action}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
