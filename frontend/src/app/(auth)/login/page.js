"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ShieldCheck, Loader2, MailCheck, CircleAlert } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { toast } from "sonner";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setNotice(null);

    const supabase = createClient();
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error || !data.session?.access_token) {
      setError("Invalid username or password. Please try again.");
      setLoading(false);
      return;
    }
    try {
      const response = await fetch(`${API_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${data.session.access_token}` },
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.error?.message || "This account is not authorised for staff access.");
      }
      router.replace("/dashboard");
      router.refresh();
    } catch (requestError) {
      await supabase.auth.signOut();
      setError(requestError.message || "The SmartFinn API is unavailable.");
      setLoading(false);
    }
  };

  const handleForgotPassword = () => {
    toast.warning("Please contact the administrator.");
  };

  const handleRequestAccess = () => {
    toast.warning("Please contact the administrator.");
  };

  return (
    <div className="grid min-h-dvh w-full lg:grid-cols-2">
      {/* Left Pane - Branding */}
      <div className="relative hidden flex-col justify-between overflow-hidden bg-slate-950 p-12 text-white lg:flex">
        {/* Abstract Geometric Background */}
        <div className="absolute inset-0 opacity-10 bg-[linear-gradient(45deg,transparent_25%,rgba(68,107,158,1)_50%,transparent_75%,transparent_100%)] bg-[length:24px_24px]" />
        <div className="absolute top-0 right-0 w-96 h-96 bg-blue-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 -translate-y-1/2 translate-x-1/2" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-emerald-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 translate-y-1/2 -translate-x-1/2" />
        
        <div className="relative z-10 flex items-center space-x-3">
          <ShieldCheck className="h-10 w-10 text-blue-400" />
          <span className="text-2xl font-semibold tracking-tight">SmartFINN</span>
        </div>
        
        <div className="relative z-10 max-w-md">
          <h1 className="mb-6 text-4xl font-semibold leading-tight tracking-tight">
            Mortgage compliance, made reviewable.
          </h1>
          <p className="text-lg text-slate-300">
            Extract documents, verify key fields and assess application risk in one secure workspace.
          </p>
        </div>
        
        <div className="relative z-10 text-sm text-slate-500">
          © 2026 SmartFINN
        </div>
      </div>

      {/* Right Pane - Login Form */}
      <div className="flex items-center justify-center bg-white p-6 sm:p-8">
        <div className="w-full max-w-md space-y-8">
          <div className="flex items-center gap-2 text-slate-950 lg:hidden"><ShieldCheck className="h-5 w-5 text-blue-600" /><span className="font-semibold tracking-tight">SmartFINN</span></div>
          <div className="text-center lg:text-left">
            <h2 className="mb-2 text-3xl font-semibold tracking-tight text-slate-950">
              Welcome back
            </h2>
            <p className="text-sm text-slate-500">
              Sign in with your authorised staff account.
            </p>
          </div>

          <form className="space-y-6" onSubmit={handleLogin}>
            {error && (
              <div className="flex gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700" role="alert"><CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />
                {error}
              </div>
            )}
            {notice && <div className="flex gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700"><MailCheck className="mt-0.5 h-4 w-4 shrink-0" />{notice}</div>}
            
            <div className="space-y-2">
              <Label htmlFor="email">Email address</Label>
              <Input 
                id="email" 
                type="email" 
                placeholder="reviewer@smartfinn.app"
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

            <div className="flex justify-end">
              <button type="button" onClick={handleForgotPassword} className="text-sm font-medium text-blue-600 hover:text-blue-700 disabled:opacity-50">
                Forgot Password?
              </button>
            </div>

            <Button type="submit" disabled={loading} className="w-full h-12 text-base font-medium bg-blue-600 hover:bg-blue-700">
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Signing In...
                </>
              ) : (
                "Sign in"
              )}
            </Button>
          </form>

          <div className="text-center pt-4">
            <p className="text-sm text-slate-500">
              Don&apos;t have an account?{" "}
              <button 
                type="button" 
                onClick={handleRequestAccess} 
                className="font-semibold text-blue-600 hover:text-blue-700"
              >
                Request Access
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
