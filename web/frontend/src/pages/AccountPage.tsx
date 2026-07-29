import { useEffect, useRef, useState } from "react";
import { me, uploadAvatar, type MeResponse } from "../api";
import { Avatar } from "../components/Avatar";
import { errorMessage } from "../lib/errorMessage";

export default function AccountPage() {
  const [user, setUser] = useState<MeResponse | null>(null);
  const [error, setError] = useState<string>("");
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    me().then(setUser).catch(() => setUser(null));
  }, []); //set the user on load

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    setUploading(true);
    try {
      const { avatar_url } = await uploadAvatar(file);
      setUser((u) => (u ? { ...u, avatar_url } : u));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = ""; // allow re-selecting the same file
    }
  }

  if (!user) return <p className="mx-auto max-w-md px-4 py-8 text-zinc-400">Loading…</p>;

  return (
    <div className="mx-auto max-w-md px-4 py-8">
      <h2 className="mb-6 text-2xl font-bold text-white">Account</h2>

      <div className="flex items-center gap-4 rounded-2xl bg-zinc-900 p-6">
        <Avatar url={user.avatar_url} name={user.username} size={80} />
        <div>
          <p className="font-semibold text-white">{user.username}</p>
          <p className="mb-2 text-sm text-zinc-400">{user.email}</p>
          <button
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="rounded-lg bg-red-600 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-red-500 disabled:opacity-60"
          >
            {uploading ? "Uploading…" : "Change photo"}
          </button>
        </div>
      </div>

      <input
        ref={fileRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={onFile}
        className="hidden"
      />

      <p className="mt-3 text-xs text-zinc-500">JPEG, PNG, or WebP · up to 5 MB.</p>
      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
    </div>
  );
}
