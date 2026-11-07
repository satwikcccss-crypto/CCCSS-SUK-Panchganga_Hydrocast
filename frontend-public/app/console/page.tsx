import { redirect } from "next/navigation";

export default function ConsoleRedirect() {
  redirect("http://localhost:3001/admin");
}
