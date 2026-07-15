import { Link } from "react-router-dom";

export default function CoinsCancelPage() {
  return (
    <div className="w-full px-6 py-8 text-left">
      <div className="mx-auto max-w-md text-center">
        <h1 className="mt-10 text-2xl font-bold text-white">Checkout cancelled</h1>
        <p className="mt-2 text-sm text-zinc-400">
          no charges were taken
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <Link
            to="/coins"
            className="rounded-lg bg-red-600 px-5 py-2.5 font-semibold text-white transition-colors hover:bg-red-500"
          >
            Back to coins
          </Link>
          <Link
            to="/rooms"
            className="rounded-lg border border-zinc-700 px-5 py-2.5 text-zinc-300 transition-colors hover:border-red-500/60 hover:text-white"
          >
            Lobby
          </Link>
        </div>
      </div>
    </div>
  );
}
