const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";

export function withBasePath(pathname) {
  const path = pathname?.startsWith("/") ? pathname : `/${pathname || ""}`;
  if (!BASE_PATH || path === BASE_PATH || path.startsWith(`${BASE_PATH}/`)) return path;
  return `${BASE_PATH}${path}`;
}

function withoutBasePath(pathname) {
  if (!BASE_PATH) return pathname;
  if (pathname === BASE_PATH) return "/";
  return pathname.startsWith(`${BASE_PATH}/`) ? pathname.slice(BASE_PATH.length) : pathname;
}

export function safeRedirectPath(value, fallback = "/update-password") {
  return value?.startsWith("/") && !value.startsWith("//") ? value : fallback;
}

export function isPublicPath(pathname) {
  const path = withoutBasePath(pathname);
  return path === "/" || path.startsWith("/login") || path.startsWith("/auth/");
}
