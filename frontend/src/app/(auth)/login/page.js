"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { ShieldCheck, Loader2 } from "lucide-react";
import Link from "next/link";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Check if there is a session already or if we are returning from an invite link
    const checkSession = async () => {
      // Supabase automatically parses the hash fragment and establishes a session
      const { data: { session } } = await supabase.auth.getSession();
      
      if (session) {
        // If we got here with an invite link, redirect to update password
        const hash = window.location.hash;
        if (hash && hash.includes("type=invite")) {
          router.push("/update-password");
        } else {
          // Already logged in normally
          router.push("/dashboard");
        }
      }
    };
    
    checkSession();

    // Also listen to auth changes in case the session is established after mount
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_IN" || event === "INITIAL_SESSION") {
        if (session) {
           const hash = window.location.hash;
           if (hash && hash.includes("type=invite")) {
             router.push("/update-password");
           } else {
             router.push("/dashboard");
           }
        }
      }
    });

    return () => subscription.unsubscribe();
  }, [router]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) {
      setError("Invalid username or password. Please try again.");
      setLoading(false);
    } else {
      // Success - router will push via the onAuthStateChange listener
    }
  };

  return (
    <div className="w-full h-screen grid lg:grid-cols-2">
      {/* Left Pane - Branding */}
      <div className="hidden lg:flex flex-col justify-between bg-slate-900 p-12 text-white relative overflow-hidden">
        {/* Abstract Geometric Background */}
        <div className="absolute inset-0 opacity-20 bg-[linear-gradient(45deg,transparent_25%,rgba(68,107,158,1)_50%,transparent_75%,transparent_100%)] bg-[length:20px_20px]" />
        <div className="absolute top-0 right-0 w-96 h-96 bg-blue-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 -translate-y-1/2 translate-x-1/2" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-emerald-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 translate-y-1/2 -translate-x-1/2" />
        
        <div className="relative z-10 flex items-center space-x-3">
          <ShieldCheck className="h-10 w-10 text-blue-400" />
          <span className="text-3xl font-bold tracking-tight">SmartFinn</span>
        </div>
        
        <div className="relative z-10 max-w-md">
          <h1 className="text-4xl font-bold mb-6 leading-tight">
            Mortgage Compliance Management Platform
          </h1>
          <p className="text-lg text-slate-300">
            Secure. Reliable. Compliant. Automate document verification and streamline your risk assessment workflows.
          </p>
        </div>
        
        <div className="relative z-10 text-sm text-slate-500">
          © 2026 SmartFinn Inc.
        </div>
      </div>

      {/* Right Pane - Login Form */}
      <div className="flex items-center justify-center p-8 bg-white">
        <div className="w-full max-w-md space-y-8">
          <div className="text-center lg:text-left">
            <h2 className="text-3xl font-bold tracking-tight text-slate-900 mb-2">
              Sign In to Your Account
            </h2>
            <p className="text-sm text-slate-500">
              Enter your credentials to access the platform.
            </p>
          </div>

          <form className="space-y-6" onSubmit={handleLogin}>
            {error && (
              <div className="p-3 rounded-md bg-red-50 border border-red-200 text-sm text-red-600">
                {error}
              </div>
            )}
            
            <div className="space-y-2">
              <Label htmlFor="email">Email Address / Username</Label>
              <Input 
                id="email" 
                type="email" 
                placeholder="john.doe@enterprise.com" 
                required 
                className="h-12"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input 
                id="password" 
                type="password" 
                placeholder="••••••••" 
                required 
                className="h-12"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Checkbox id="remember" disabled={loading} />
                <label 
                  htmlFor="remember" 
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                >
                  Remember Me
                </label>
              </div>
              <Link href="#" className="text-sm font-medium text-blue-600 hover:text-blue-500">
                Forgot Password?
              </Link>
            </div>

            <Button type="submit" disabled={loading} className="w-full h-12 text-base font-medium bg-blue-600 hover:bg-blue-700">
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Signing In...
                </>
              ) : (
                "Sign In"
              )}
            </Button>
          </form>

          <div className="text-center pt-6">
            <p className="text-sm text-slate-500">
              Don&apos;t have an account?{' '}
              <Link href="#" className="font-semibold text-blue-600 hover:text-blue-500">
                Request Access
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
