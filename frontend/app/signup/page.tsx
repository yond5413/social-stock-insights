"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { motion } from "framer-motion"
import { createClient } from "@/lib/supabase/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { GradientText } from "@/components/ui/gradient-text"
import { Sparkles, Check, Loader2, Shield, Zap, Target } from "lucide-react"

export default function SignupPage() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  // Password strength calculator
  const getPasswordStrength = (pass: string) => {
    if (!pass) return 0
    let strength = 0
    if (pass.length >= 8) strength += 25
    if (pass.length >= 12) strength += 25
    if (/[a-z]/.test(pass) && /[A-Z]/.test(pass)) strength += 25
    if (/[0-9]/.test(pass)) strength += 15
    if (/[^a-zA-Z0-9]/.test(pass)) strength += 10
    return Math.min(strength, 100)
  }

  const passwordStrength = getPasswordStrength(password)
  const getStrengthColor = () => {
    if (passwordStrength < 40) return "bg-red-500"
    if (passwordStrength < 70) return "bg-yellow-500"
    return "bg-green-500"
  }

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setMessage(null)

    const supabase = createClient()
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: `${process.env.NEXT_PUBLIC_SITE_URL || window.location.origin}/auth/callback`,
      },
    })

    if (error) {
      setError(error.message)
    } else {
      setMessage("Account created! Check your email for confirmation.")
      setTimeout(() => router.push("/login"), 3000)
    }
    setLoading(false)
  }

  const features = [
    { icon: Zap, text: "AI-driven sentiment from social media" },
    { icon: Target, text: "Community-powered stock insights" },
    { icon: Shield, text: "Free access to market analytics" },
  ]

  return (
    <div className="flex min-h-screen">
      {/* Left Side - Animated Gradient Background */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-gradient-to-br from-blue-600 via-slate-600 to-blue-800 p-12">
        {/* Animated Background Pattern */}
        <div className="absolute inset-0 bg-grid opacity-10"></div>
        <motion.div
          className="absolute inset-0 bg-gradient-to-br from-blue-500/20 via-slate-500/20 to-blue-500/20"
          animate={{
            backgroundPosition: ['0% 0%', '100% 100%', '0% 0%'],
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            ease: "linear"
          }}
        />

        {/* Content */}
        <div className="relative z-10 flex flex-col justify-between text-white">
          {/* Logo */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-3"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/20 backdrop-blur-sm">
              <Sparkles className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">Stock Insights</h1>
              <p className="text-sm text-white/80">AI-Powered Analysis</p>
            </div>
          </motion.div>

          {/* Main Content */}
          <div className="space-y-8">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <h2 className="text-4xl font-bold leading-tight mb-4">
                Start Your Journey to
                <br />
                Smarter Investing
              </h2>
              <p className="text-lg text-white/80">
                Join a growing community discovering AI-powered insights from real social sentiment.
              </p>
            </motion.div>

            {/* Features */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="space-y-4"
            >
              {features.map((feature, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.5 + index * 0.1 }}
                  className="flex items-center gap-4 glass-card p-4 rounded-xl"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/20">
                    <feature.icon className="h-5 w-5" />
                  </div>
                  <p className="text-lg font-medium">{feature.text}</p>
                </motion.div>
              ))}
            </motion.div>
          </div>

          {/* Community Indicators */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
            className="space-y-3"
          >
            <p className="text-sm text-white/60 uppercase tracking-wider">Join our community</p>
            <div className="flex gap-6 items-center opacity-80">
              <div className="text-lg font-semibold">Get Started</div>
              <div className="text-lg font-semibold">AI-Powered</div>
              <div className="text-lg font-semibold">Real-Time</div>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Right Side - Signup Form */}
      <div className="flex-1 flex items-center justify-center p-6 md:p-12 bg-background">
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="w-full max-w-md"
        >
          <Card className="glass-card border-border/50 shadow-xl">
            <CardHeader className="space-y-1 pb-6">
              {/* Mobile Logo */}
              <div className="lg:hidden flex items-center gap-2 mb-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-slate-500">
                  <Sparkles className="h-5 w-5 text-white" />
                </div>
                <GradientText className="text-xl font-bold">Stock Insights</GradientText>
              </div>

              <CardTitle className="text-2xl font-bold">Create an account</CardTitle>
              <CardDescription>
                Start analyzing stocks with AI-powered insights
              </CardDescription>
            </CardHeader>
            <form onSubmit={handleSignup}>
              <CardContent className="space-y-4">
                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-3 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/30 rounded-lg"
                  >
                    {error}
                  </motion.div>
                )}
                {message && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-3 text-sm text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-900/30 rounded-lg flex items-center gap-2"
                  >
                    <Check className="h-4 w-4" />
                    {message}
                  </motion.div>
                )}
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="name@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="h-11"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="h-11"
                  />
                  {password && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      className="space-y-1"
                    >
                      <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                        <motion.div
                          className={`h-full ${getStrengthColor()}`}
                          initial={{ width: 0 }}
                          animate={{ width: `${passwordStrength}%` }}
                          transition={{ duration: 0.3 }}
                        />
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Password strength: {
                          passwordStrength < 40 ? "Weak" :
                            passwordStrength < 70 ? "Medium" : "Strong"
                        }
                      </p>
                    </motion.div>
                  )}
                </div>
                <p className="text-xs text-muted-foreground">
                  By creating an account, you agree to our{" "}
                  <Link href="#" className="text-primary hover:underline">
                    Terms of Service
                  </Link>{" "}
                  and{" "}
                  <Link href="#" className="text-primary hover:underline">
                    Privacy Policy
                  </Link>
                  .
                </p>
              </CardContent>
              <CardFooter className="flex flex-col space-y-4">
                <Button
                  type="submit"
                  className="w-full h-11 bg-gradient-to-r from-blue-500 to-slate-500 hover:from-blue-600 hover:to-slate-600 text-white font-medium"
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Creating account...
                    </>
                  ) : (
                    "Create account"
                  )}
                </Button>
                <div className="text-sm text-center text-muted-foreground">
                  Already have an account?{" "}
                  <Link href="/login" className="text-primary hover:underline font-medium">
                    Sign in
                  </Link>
                </div>
              </CardFooter>
            </form>
          </Card>
        </motion.div>
      </div>
    </div>
  )
}
