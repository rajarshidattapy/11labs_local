import {
  clerkMiddleware,
  createRouteMatcher,
} from "@clerk/nextjs/server";

const isAuthRoute = createRouteMatcher(["/app/sign-in(.*)", "/app/sign-up(.*)"]);
const isProtectedRoute = createRouteMatcher(["/app/(.*)"]);

export default clerkMiddleware(async (auth, request) => {
  const { userId } = await auth();

  if (userId && isAuthRoute(request)) {
    const url = new URL("/app/speech-synthesis/text-to-speech", request.url);
    return Response.redirect(url);
  }

  if (!userId && isProtectedRoute(request) && !isAuthRoute(request)) {
    await auth.protect();
  }
});

export const config = {
  matcher: ["/app/:path*"],
};
