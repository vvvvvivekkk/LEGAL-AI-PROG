import { motion } from 'framer-motion'

// Wraps a routed page in a short fade + rise. Reduced-motion users get the
// near-instant transition enforced globally in styles.css.
export default function PageTransition({ children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.22, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  )
}
