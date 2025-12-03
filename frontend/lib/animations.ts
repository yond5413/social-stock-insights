import { Variants } from 'framer-motion'

// Fade in from bottom
export const fadeInUp: Variants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 }
}

// Stagger children animations
export const staggerContainer: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.1
    }
  }
}

// Scale and fade
export const scaleIn: Variants = {
  initial: { opacity: 0, scale: 0.9 },
  animate: { 
    opacity: 1, 
    scale: 1,
    transition: {
      type: "spring",
      stiffness: 300,
      damping: 20
    }
  },
  exit: { opacity: 0, scale: 0.9 }
}

// Slide from side
export const slideInRight: Variants = {
  initial: { opacity: 0, x: 50 },
  animate: { 
    opacity: 1, 
    x: 0,
    transition: {
      type: "spring",
      stiffness: 200,
      damping: 20
    }
  },
  exit: { opacity: 0, x: 50 }
}

// Card hover animation
export const cardHover: Variants = {
  rest: { scale: 1 },
  hover: { 
    scale: 1.02,
    y: -4,
    transition: {
      type: "spring",
      stiffness: 400,
      damping: 10
    }
  }
}

// Button tap animation
export const buttonTap = {
  scale: 0.95,
  transition: { duration: 0.1 }
}

// Spring configuration
export const springConfig = {
  type: "spring" as const,
  stiffness: 300,
  damping: 25
}

// Smooth spring
export const smoothSpring = {
  type: "spring" as const,
  stiffness: 200,
  damping: 20
}

// Page transition
export const pageTransition: Variants = {
  initial: { opacity: 0, x: -20 },
  animate: { 
    opacity: 1, 
    x: 0,
    transition: {
      duration: 0.4,
      ease: "easeOut"
    }
  },
  exit: { 
    opacity: 0, 
    x: 20,
    transition: {
      duration: 0.3,
      ease: "easeIn"
    }
  }
}







