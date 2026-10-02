export function LoadingScreen({ message = 'Checking your session...' }: { message?: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 text-slate-900">
      <div className="rounded-xl border border-slate-200 bg-white px-6 py-5 text-center shadow-sm">
        <div className="mx-auto mb-3 h-6 w-6 animate-spin rounded-full border-2 border-slate-300 border-t-slate-900" />
        <p className="text-sm font-medium text-slate-700">{message}</p>
      </div>
    </div>
  )
}
