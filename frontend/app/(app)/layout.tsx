import NavBar from "@/components/NavBar";

// Shell for all authenticated pages. NavBar handles the client-side auth guard
// (redirects to /login when there's no token). /login lives outside this group.
export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="app-shell">
      <NavBar />
      <main className="main">{children}</main>
    </div>
  );
}
