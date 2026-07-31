export function safeRedirectPath(value, fallback = "/update-password") {
  return value?.startsWith("/") && !value.startsWith("//") ? value : fallback;
}

export function isPublicPath(pathname) {
  return pathname === "/" || pathname.startsWith("/login") || pathname.startsWith("/auth/");
}
