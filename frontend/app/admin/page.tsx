import { redirect } from "next/navigation";

export default function AdminRedirect() {
  redirect("http://localhost:3001/admin");
}
