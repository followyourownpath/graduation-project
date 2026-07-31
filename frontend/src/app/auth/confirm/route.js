import { NextResponse } from "next/server";
import { safeRedirectPath } from "@/lib/auth-utils";
import { createClient } from "@/lib/supabase/server";

export async function GET(request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const tokenHash = url.searchParams.get("token_hash");
  const type = url.searchParams.get("type");
  const next = safeRedirectPath(url.searchParams.get("next"));
  const supabase = await createClient();

  let error;
  if (code) {
    ({ error } = await supabase.auth.exchangeCodeForSession(code));
  } else if (tokenHash && type) {
    ({ error } = await supabase.auth.verifyOtp({ token_hash: tokenHash, type }));
  } else {
    error = new Error("Missing confirmation token");
  }

  if (!error) return NextResponse.redirect(new URL(next, request.url));
  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("error", "invalid_or_expired_link");
  return NextResponse.redirect(loginUrl);
}
