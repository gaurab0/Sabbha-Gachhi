import { Outlet } from "react-router-dom";
import { Footer, Navbar } from "../components/chrome";

export function PublicLayout() {
  return (
    <>
      <Navbar />
      <Outlet />
      <Footer />
    </>
  );
}
