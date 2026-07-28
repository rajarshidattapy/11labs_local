import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="flex min-h-screen w-full items-center justify-center">
      <SignUp />
    </div>
  );
}
