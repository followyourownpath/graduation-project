"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ShieldCheck, Loader2, CheckCircle2 } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

export default function UpdatePasswordPage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    // Ensure the user actually has a session (they must be authenticated via the invite link to update their password)
    const checkSession = async () => {
      const { data: { session } } = await createClient().auth.getSession();
      if (!session) {
        // If no session is found, they probably navigated here directly without an invite token
        router.push("/login");
      }
    };
    checkSession();
  }, [router]);

  const handleUpdatePassword = async (e) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters long.");
      return;
    }

    setLoading(true);

    const { error } = await createClient().auth.updateUser({
      password: password
    });

    if (error) {
      setError(error.message || "Failed to update password. Please try again.");
      setLoading(false);
    } else {
      setSuccess(true);
      // Wait a moment to show the success message, then redirect to dashboard
      setTimeout(() => {
        router.push("/dashboard");
      }, 2000);
    }
  };

  return (
    <div className="w-full h-screen grid lg:grid-cols-2">
      {/* Left Pane - Branding */}
      <div className="hidden lg:flex flex-col justify-between bg-slate-900 p-12 text-white relative overflow-hidden">
        <div className="absolute inset-0 opacity-20 bg-[linear-gradient(45deg,transparent_25%,rgba(68,107,158,1)_50%,transparent_75%,transparent_100%)] bg-[length:20px_20px]" />
        <div className="absolute top-0 right-0 w-96 h-96 bg-blue-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 -translate-y-1/2 translate-x-1/2" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-emerald-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 translate-y-1/2 -translate-x-1/2" />
        
        <div className="relative z-10 flex items-center space-x-3">
          <ShieldCheck className="h-10 w-10 text-blue-400" />
          <span className="text-3xl font-bold tracking-tight">SmartFinn</span>
        </div>
        
        <div className="relative z-10 max-w-md">
          <h1 className="text-4xl font-bold mb-6 leading-tight">
            Welcome to the Team
          </h1>
          <p className="text-lg text-slate-300">
            Please set your initial password to activate your compliance reviewer account.
          </p>
        </div>
        
        <div className="relative z-10 text-sm text-slate-500">
          © 2026 SmartFinn Inc.
        </div>
      </div>

      {/* Right Pane - Update Password Form */}
      <div className="flex items-center justify-center p-8 bg-white">
        <div className="w-full max-w-md space-y-8">
          <div className="text-center lg:text-left">
            <h2 className="text-3xl font-bold tracking-tight text-slate-900 mb-2">
              Set Your Password
            </h2>
            <p className="text-sm text-slate-500">
              Your email has been verified. Choose a secure password to continue.
            </p>
          </div>

          {success ? (
            <div className="p-6 rounded-lg bg-emerald-50 border border-emerald-200 text-center space-y-4">
              <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto" />
              <h3 className="text-lg font-medium text-emerald-900">Password Set Successfully!</h3>
              <p className="text-sm text-emerald-700">Redirecting you to the dashboard...</p>
            </div>
          ) : (
            <form className="space-y-6" onSubmit={handleUpdatePassword}>
              {error && (
                <div className="p-3 rounded-md bg-red-50 border border-red-200 text-sm text-red-600">
                  {error}
                </div>
              )}
              
              <div className="space-y-2">
                <Label htmlFor="password">New Password</Label>
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

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm Password</Label>
                <Input 
                  id="confirmPassword" 
                  type="password" 
                  placeholder="••••••••" 
                  required 
                  className="h-12"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={loading}
                />
              </div>

              <Button type="submit" disabled={loading} className="w-full h-12 text-base font-medium bg-blue-600 hover:bg-blue-700">
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Saving Password...
                  </>
                ) : (
                  "Set Password & Continue"
                )}
              </Button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
