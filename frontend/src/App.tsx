import { useRef, useState, type FormEvent, type ReactNode } from 'react'
import { ResumeAnalysisView } from './components/ResumeAnalysisView'
import { ApiClientError, uploadAndAnalyzeResume } from './services/apiClient'
import type { ResumeAnalysisResult } from './types'

type Page = 'Overview' | 'My resumes' | 'Job tracker' | 'Career profile'
type Resume = { id: number; name: string; updated: string; size: string; score: number; color: string; pageCount?: number; analysis?: ResumeAnalysisResult; pdfFile?: File }
type Application = { id: number; role: string; company: string; date: string; status: string; color: string }

const initialResumes: Resume[] = [
  { id: 1, name: 'Product Designer Resume.pdf', updated: 'Updated today', size: '248 KB', score: 86, color: 'violet' },
  { id: 2, name: 'UX Research Portfolio.pdf', updated: 'Updated Sep 28, 2026', size: '1.2 MB', score: 78, color: 'amber' },
  { id: 3, name: 'General Resume 2026.pdf', updated: 'Updated Sep 21, 2026', size: '196 KB', score: 72, color: 'blue' },
]

const initialApplications: Application[] = [
  { id: 1, role: 'Senior Product Designer', company: 'Notion', date: 'Oct 01, 2026', status: 'Interview', color: 'violet' },
  { id: 2, role: 'Product Designer', company: 'Linear', date: 'Sep 29, 2026', status: 'Applied', color: 'blue' },
  { id: 3, role: 'UX Designer', company: 'Figma', date: 'Sep 26, 2026', status: 'In review', color: 'amber' },
]

const navItems: { label: Page; icon: string }[] = [
  { label: 'Overview', icon: 'grid' },
  { label: 'My resumes', icon: 'file' },
  { label: 'Job tracker', icon: 'briefcase' },
  { label: 'Career profile', icon: 'user' },
]

const icons: Record<string, ReactNode> = {
  grid: <><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /></>,
  file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6M8 13h8M8 17h8" /></>,
  briefcase: <><rect x="3" y="7" width="18" height="14" rx="2" /><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18M10 12v2h4v-2" /></>,
  user: <><path d="M20 21a8 8 0 0 0-16 0" /><circle cx="12" cy="8" r="4" /></>,
  settings: <><circle cx="12" cy="12" r="3" /><path d="m19.4 15 .1.1 1.4 1.1-1.4 2.4-1.7-.6a8 8 0 0 1-1.8 1l-.3 1.8h-2.8l-.3-1.8a8 8 0 0 1-1.8-1l-1.7.6-1.4-2.4 1.4-1.1a8 8 0 0 1 0-2l-1.4-1.1 1.4-2.4 1.7.6a8 8 0 0 1 1.8-1l.3-1.8h2.8l.3 1.8a8 8 0 0 1 1.8 1l1.7-.6 1.4 2.4-1.4 1.1a8 8 0 0 1 0 2Z" /></>,
  help: <><circle cx="12" cy="12" r="10" /><path d="M9.6 9a2.5 2.5 0 1 1 4.3 1.7c-1.2 1.2-1.9 1.5-1.9 3.3M12 17h.01" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
  bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></>,
  plus: <><path d="M12 5v14M5 12h14" /></>,
  arrow: <><path d="M7 17 17 7M7 7h10v10" /></>,
  upload: <><path d="M12 16V4m0 0L7 9m5-5 5 5" /><path d="M20 16v3a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-3" /></>,
  dots: <><circle cx="5" cy="12" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="19" cy="12" r="1" /></>,
  clock: <><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></>,
  check: <path d="m5 12 4 4L19 6" />,
  spark: <><path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-2-5.8L4 11l6-2.2L12 3Z" /><path d="m19 14 1 2.5 2 1-2 1-1 2.5-1-2.5-2-1 2-1 1-2.5Z" /></>,
  trend: <><path d="m3 17 6-6 4 4 8-8" /><path d="M15 7h6v6" /></>,
  calendar: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M16 3v4M8 3v4M3 11h18" /></>,
  close: <><path d="m18 6-12 12M6 6l12 12" /></>,
  chevron: <path d="m9 18 6-6-6-6" />,
}

function Icon({ name, size = 18, className = '' }: { name: string; size?: number; className?: string }) {
  return (
    <svg aria-hidden="true" className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      {icons[name]}
    </svg>
  )
}

function StatusBadge({ status }: { status: string }) {
  const color = status === 'Interview' ? 'bg-violet-50 text-violet-700' : status === 'Applied' ? 'bg-blue-50 text-blue-700' : 'bg-amber-50 text-amber-700'
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${color}`}>{status}</span>
}

function App() {
  const [page, setPage] = useState<Page>('Overview')
  const [resumes, setResumes] = useState(initialResumes)
  const [applications, setApplications] = useState(initialApplications)
  const [search, setSearch] = useState('')
  const [toast, setToast] = useState('')
  const [profileName, setProfileName] = useState('Alex Morgan')
  const [profileRole, setProfileRole] = useState('Product Designer')
  const [profileLocation, setProfileLocation] = useState('San Francisco, CA')
  const [newApplicationOpen, setNewApplicationOpen] = useState(false)
  const [newRole, setNewRole] = useState('')
  const [newCompany, setNewCompany] = useState('')
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [analysisResume, setAnalysisResume] = useState<Resume | null>(null)
  const [selectedApplication, setSelectedApplication] = useState<Application | null>(null)
  const [activityRange, setActivityRange] = useState<'30 days' | '6 months' | '12 months'>('6 months')
  const [rangeMenuOpen, setRangeMenuOpen] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  const notify = (message: string) => {
    setToast(message)
    window.setTimeout(() => setToast((current) => current === message ? '' : current), 3200)
  }

  const addResume = async (file?: File) => {
    if (!file) return
    setUploading(true)
    setUploadError('')
    try {
      const response = await uploadAndAnalyzeResume(file)
      const size = file.size < 1024 * 1024 ? `${Math.max(1, Math.round(file.size / 1024))} KB` : `${(file.size / (1024 * 1024)).toFixed(1)} MB`
      const resume: Resume = {
        id: Date.now(),
        name: response.filename,
        updated: 'Added just now',
        size,
        score: 0,
        color: 'emerald',
        pageCount: response.page_count,
        analysis: response.result,
        pdfFile: file,
      }
      setResumes((items) => [resume, ...items])
      setPage('My resumes')
      setAnalysisResume(resume)
      notify(`AI analysis complete for ${response.filename}.`)
      setUploadError('')
    } catch (error) {
      let message: string
      if (error instanceof ApiClientError && error.body.code === 'AI_CONFIGURATION_ERROR') {
        message = 'AI is not configured. Check the selected provider and its required settings in the project .env, then restart the API.'
      } else if (error instanceof ApiClientError) {
        message = error.body.message
      } else {
        message = error instanceof Error ? error.message : 'The selected PDF could not be analyzed.'
      }
      setUploadError(message)
      notify(message)
    } finally {
      setUploading(false)
    }
  }

  const createApplication = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!newRole.trim() || !newCompany.trim()) return
    setApplications((items) => [
      { id: Date.now(), role: newRole.trim(), company: newCompany.trim(), date: 'Today', status: 'Applied', color: 'blue' },
      ...items,
    ])
    setNewRole('')
    setNewCompany('')
    setNewApplicationOpen(false)
    notify('Application added to your tracker.')
  }

  const filteredResumes = resumes.filter((item) => item.name.toLowerCase().includes(search.toLowerCase()))
  const filteredApplications = applications.filter((item) => `${item.role} ${item.company} ${item.status}`.toLowerCase().includes(search.toLowerCase()))
  const updateApplicationStatus = (id: number, status: string) => {
    setApplications((items) => items.map((item) => item.id === id ? { ...item, status } : item))
    setSelectedApplication((item) => item?.id === id ? { ...item, status } : item)
    notify('Application status updated.')
  }
  const openResumePdf = (resume: Resume) => {
    if (!resume.pdfFile) {
      notify('The original file is available only until this page is refreshed. Upload it again to open it.')
      return
    }
    const url = URL.createObjectURL(resume.pdfFile)
    const openedWindow = window.open(url, '_blank', 'noopener,noreferrer')
    if (!openedWindow) notify('Your browser blocked the PDF window. Allow pop-ups and try again.')
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
  }

  const goTo = (destination: Page) => {
    setPage(destination)
    setSearch('')
    setMobileNavOpen(false)
  }

  const uploadButton = (label = 'Upload resume', primary = true) => (
    <>
      <button disabled={uploading} onClick={() => fileInput.current?.click()} className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition disabled:cursor-wait disabled:opacity-70 ${primary ? 'bg-indigo-600 text-white shadow-sm hover:bg-indigo-700' : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'}`}>
        <Icon name={uploading ? 'clock' : 'upload'} size={16} />{uploading ? 'Reading PDF…' : label}
      </button>
      <input
        ref={fileInput}
        type="file"
        aria-label="Upload resume PDF"
        accept=".pdf,application/pdf"
        className="hidden"
        onChange={(event) => {
          void addResume(event.target.files?.[0])
          event.currentTarget.value = ''
        }}
      />
    </>
  )

  return (
    <div className="min-h-screen bg-[#f7f8fc] text-slate-900">
      {mobileNavOpen && <button aria-label="Close navigation" onClick={() => setMobileNavOpen(false)} className="fixed inset-0 z-30 bg-slate-950/40 lg:hidden" />}
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-[256px] flex-col bg-[#171a2d] px-4 py-5 text-white transition-transform lg:translate-x-0 ${mobileNavOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex items-center gap-3 px-3 pb-9 pt-1">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-indigo-500 text-white"><Icon name="spark" size={21} /></div>
          <div><p className="text-[17px] font-bold tracking-tight">career<span className="text-indigo-300">ai</span></p><p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">Career workspace</p></div>
          <button aria-label="Close menu" onClick={() => setMobileNavOpen(false)} className="ml-auto rounded-lg p-2 text-slate-400 hover:bg-white/10 lg:hidden"><Icon name="close" /></button>
        </div>
        <p className="px-3 pb-3 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">Workspace</p>
        <nav aria-label="Main navigation" className="space-y-1">
          {navItems.map((item) => (
            <button key={item.label} onClick={() => goTo(item.label)} className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-[13px] font-medium transition ${page === item.label ? 'bg-indigo-500/20 text-white' : 'text-slate-400 hover:bg-white/5 hover:text-slate-100'}`}>
              <Icon name={item.icon} size={17} className={page === item.label ? 'text-indigo-300' : ''} />{item.label}
              {item.label === 'Job tracker' && <span className="ml-auto rounded-md bg-white/10 px-1.5 py-0.5 text-[10px] text-slate-300">{applications.length}</span>}
            </button>
          ))}
        </nav>
        <div className="mt-auto">
          <div className="mb-5 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <div className="mb-3 flex items-center justify-between"><span className="text-xs font-semibold text-slate-200">Profile strength</span><span className="text-xs font-bold text-indigo-300">78%</span></div>
            <div className="h-1.5 overflow-hidden rounded-full bg-white/10"><div className="h-full w-[78%] rounded-full bg-indigo-400" /></div>
            <p className="mt-3 text-[11px] leading-relaxed text-slate-400">Add your work experience to stand out to recruiters.</p>
            <button onClick={() => goTo('Career profile')} className="mt-3 text-[11px] font-semibold text-indigo-300 hover:text-indigo-200">Complete profile <span aria-hidden="true">→</span></button>
          </div>
          <button onClick={() => notify('Settings are available in the full product.')} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium text-slate-400 hover:bg-white/5 hover:text-white"><Icon name="settings" size={17} />Settings</button>
          <button onClick={() => notify('Help center is coming soon.')} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium text-slate-400 hover:bg-white/5 hover:text-white"><Icon name="help" size={17} />Help & support</button>
          <div className="mt-4 flex items-center gap-3 border-t border-white/10 px-2 pt-4">
            <div className="grid h-9 w-9 place-items-center rounded-full bg-[#f1d4c8] text-xs font-bold text-[#764a40]">AM</div>
            <div className="min-w-0 flex-1"><p className="truncate text-xs font-semibold">{profileName}</p><p className="truncate text-[10px] text-slate-400">Free plan · Preview</p></div>
            <button aria-label="Open career profile" onClick={() => goTo('Career profile')} className="rounded-md p-1 text-slate-400 hover:bg-white/10"><Icon name="dots" size={17} /></button>
          </div>
        </div>
      </aside>

      <div className="min-h-screen lg:pl-[256px]">
        <header className="sticky top-0 z-20 flex h-[68px] items-center justify-between border-b border-slate-200/80 bg-white/90 px-4 backdrop-blur sm:px-7 lg:px-9">
          <div className="flex items-center gap-3">
            <button aria-label="Open navigation" onClick={() => setMobileNavOpen(true)} className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden"><Icon name="grid" /></button>
            <div className="hidden items-center gap-2 text-xs text-slate-400 sm:flex"><span>Workspace</span><Icon name="chevron" size={13} /><span className="font-semibold text-slate-700">{page}</span></div>
            <h1 className="text-sm font-semibold text-slate-800 sm:hidden">{page}</h1>
          </div>
          <div className="flex items-center gap-2 sm:gap-4">
            {page !== 'Career profile' && (
              <label className="hidden h-9 w-[210px] items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 sm:flex">
                <Icon name="search" size={16} className="text-slate-400" />
                <input aria-label="Search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder={`Search ${page === 'Job tracker' ? 'applications' : 'resumes'}...`} className="w-full bg-transparent text-xs outline-none placeholder:text-slate-400" />
              </label>
            )}
            <span className="hidden rounded-full bg-violet-50 px-2.5 py-1 text-[10px] font-semibold text-violet-700 sm:inline-flex">PREVIEW MODE</span>
            <button aria-label="Notifications" onClick={() => notify('You’re all caught up!')} className="relative rounded-xl p-2 text-slate-500 hover:bg-slate-100"><Icon name="bell" size={18} /><span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-indigo-500 ring-2 ring-white" /></button>
            <button onClick={() => goTo('Career profile')} className="grid h-8 w-8 place-items-center rounded-full bg-[#f1d4c8] text-[10px] font-bold text-[#764a40]">AM</button>
          </div>
        </header>

        <main className="mx-auto max-w-[1440px] px-4 py-6 sm:px-7 sm:py-8 lg:px-9">
          <div className="mb-6 flex items-center gap-2 rounded-xl border border-violet-100 bg-violet-50/80 px-3.5 py-2.5 text-xs text-violet-800">
            <Icon name="spark" size={15} className="shrink-0 text-violet-600" />
            <p><span className="font-semibold">AI resume analysis is enabled.</span> Resume text is sent to the configured AI provider; remove private information first. Dashboard figures are sample data.</p>
          </div>
          {uploadError && <div role="alert" className="mb-6 flex items-start justify-between gap-4 rounded-xl border border-red-200 bg-red-50 px-3.5 py-3 text-xs leading-relaxed text-red-800"><p>{uploadError}</p><button aria-label="Dismiss upload error" onClick={() => setUploadError('')} className="shrink-0 rounded-md px-2 py-1 font-semibold hover:bg-red-100">Dismiss</button></div>}

          {page === 'Overview' && (
            <>
              <section className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
                <div><p className="mb-1 text-xs font-semibold uppercase tracking-[0.12em] text-indigo-600">Friday, October 2, 2026</p><h2 className="text-[26px] font-bold tracking-tight sm:text-[30px]">Good morning, {profileName.split(' ')[0]} <span aria-hidden="true">✦</span></h2><p className="mt-1 text-sm text-slate-500">Here’s your career search at a glance.</p></div>
                <div className="flex gap-2">{uploadButton()}</div>
              </section>
              <section aria-label="Career search statistics" className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <StatCard icon="briefcase" title="Applications sent" value="12" trend="+3 this week" color="indigo" />
                <StatCard icon="calendar" title="Interviews" value="3" trend="1 coming up" color="amber" />
                <StatCard icon="trend" title="Profile views" value="48" trend="+18% this month" color="emerald" />
                <StatCard icon="spark" title="Resume score" value="86" suffix="/100" trend="Top 14% of profiles" color="violet" />
              </section>
              <div className="grid gap-5 xl:grid-cols-[1.55fr_1fr]">
                <section className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_2px_8px_rgba(15,23,42,.025)] sm:p-6">
                  <div className="mb-5 flex items-start justify-between"><div><h3 className="text-sm font-bold">Application activity</h3><p className="mt-1 text-xs text-slate-500">Your progress over the last {activityRange}</p></div><div className="relative"><button aria-expanded={rangeMenuOpen} onClick={() => setRangeMenuOpen((open) => !open)} className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-[11px] font-medium text-slate-600 hover:bg-slate-50">{activityRange} <span className="ml-1">⌄</span></button>{rangeMenuOpen && <div className="absolute right-0 top-full z-10 mt-1 w-32 rounded-xl border border-slate-200 bg-white p-1 shadow-lg">{(['30 days', '6 months', '12 months'] as const).map((range) => <button key={range} onClick={() => { setActivityRange(range); setRangeMenuOpen(false) }} className="block w-full rounded-lg px-3 py-2 text-left text-xs text-slate-600 hover:bg-slate-50">{range}</button>)}</div>}</div></div>
                  <div className="relative h-[210px]">
                    <div className="absolute inset-0 flex flex-col justify-between text-[10px] text-slate-400"><div className="flex items-center gap-3"><span className="w-4 text-right">20</span><div className="h-px flex-1 border-t border-dashed border-slate-200" /></div><div className="flex items-center gap-3"><span className="w-4 text-right">15</span><div className="h-px flex-1 border-t border-dashed border-slate-200" /></div><div className="flex items-center gap-3"><span className="w-4 text-right">10</span><div className="h-px flex-1 border-t border-dashed border-slate-200" /></div><div className="flex items-center gap-3"><span className="w-4 text-right">5</span><div className="h-px flex-1 border-t border-dashed border-slate-200" /></div><div className="flex items-center gap-3"><span className="w-4 text-right">0</span><div className="h-px flex-1 border-t border-dashed border-slate-200" /></div></div>
                    <svg role="img" aria-label="Application activity chart" className="absolute inset-y-0 left-8 h-[190px] w-[calc(100%-2rem)] overflow-visible" viewBox="0 0 600 190" preserveAspectRatio="none"><defs><linearGradient id="chartFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#818cf8" stopOpacity=".22" /><stop offset="100%" stopColor="#818cf8" stopOpacity="0" /></linearGradient></defs><path d="M0 152 C55 148 65 126 120 132 S185 92 240 108 S295 72 360 88 S420 40 480 62 S545 22 600 34 L600 190 L0 190Z" fill="url(#chartFill)" /><path d="M0 152 C55 148 65 126 120 132 S185 92 240 108 S295 72 360 88 S420 40 480 62 S545 22 600 34" fill="none" stroke="#6366f1" strokeWidth="3" vectorEffect="non-scaling-stroke" strokeLinecap="round" /><path d="M0 169 C60 163 75 154 120 158 S185 139 240 147 S310 126 360 133 S430 108 480 119 S550 102 600 106" fill="none" stroke="#a5b4fc" strokeWidth="2" strokeDasharray="5 5" vectorEffect="non-scaling-stroke" strokeLinecap="round" /></svg>
                    <div className="absolute bottom-0 left-8 right-0 flex justify-between text-[10px] text-slate-400"><span>May</span><span>Jun</span><span>Jul</span><span>Aug</span><span>Sep</span><span>Oct</span></div>
                  </div>
                  <div className="mt-4 flex gap-5 text-[10px] text-slate-500"><span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-indigo-500" />Applications</span><span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-indigo-200" />Profile views</span></div>
                </section>
                <section className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_2px_8px_rgba(15,23,42,.025)] sm:p-6">
                  <div className="mb-5 flex items-center justify-between"><div><h3 className="text-sm font-bold">Upcoming</h3><p className="mt-1 text-xs text-slate-500">Your next career milestones</p></div><Icon name="calendar" className="text-slate-400" size={18} /></div>
                  <div className="space-y-4">
                    <div className="flex gap-3 rounded-xl bg-violet-50/80 p-3.5"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-white text-violet-600 shadow-sm"><Icon name="calendar" size={18} /></div><div className="min-w-0 flex-1"><div className="flex items-center justify-between gap-2"><p className="truncate text-xs font-semibold">Design interview</p><span className="shrink-0 text-[10px] font-semibold text-violet-700">Oct 05</span></div><p className="mt-1 text-[11px] text-slate-500">Senior Product Designer · Notion</p><p className="mt-2 inline-flex items-center gap-1 text-[10px] text-slate-400"><Icon name="clock" size={12} />10:30 AM · Video call</p></div></div>
                    <div className="flex gap-3 rounded-xl bg-amber-50/70 p-3.5"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-white text-amber-600 shadow-sm"><Icon name="spark" size={18} /></div><div className="min-w-0 flex-1"><div className="flex items-center justify-between gap-2"><p className="truncate text-xs font-semibold">Follow up with recruiter</p><span className="shrink-0 text-[10px] font-semibold text-amber-700">Oct 06</span></div><p className="mt-1 text-[11px] text-slate-500">Product Designer · Linear</p><p className="mt-2 inline-flex items-center gap-1 text-[10px] text-slate-400"><Icon name="clock" size={12} />Send a thank-you note</p></div></div>
                    <div className="flex gap-3 rounded-xl border border-slate-100 p-3.5"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-slate-50 text-slate-500"><Icon name="file" size={18} /></div><div className="min-w-0 flex-1"><div className="flex items-center justify-between gap-2"><p className="truncate text-xs font-semibold">Update portfolio case study</p><span className="shrink-0 text-[10px] font-medium text-slate-500">Oct 09</span></div><p className="mt-1 text-[11px] text-slate-500">Add impact metrics to your latest project.</p></div></div>
                  </div>
                  <button onClick={() => goTo('Job tracker')} className="mt-4 flex w-full items-center justify-center gap-1 border-t border-slate-100 pt-4 text-xs font-semibold text-indigo-600 hover:text-indigo-800">View job tracker <Icon name="arrow" size={14} /></button>
                </section>
              </div>
              <section className="mt-5 rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_2px_8px_rgba(15,23,42,.025)] sm:p-6">
                <div className="mb-4 flex items-center justify-between"><div><h3 className="text-sm font-bold">Recent applications</h3><p className="mt-1 text-xs text-slate-500">Keep an eye on your latest opportunities</p></div><button onClick={() => goTo('Job tracker')} className="text-xs font-semibold text-indigo-600 hover:text-indigo-800">View all <span aria-hidden="true">→</span></button></div>
                <ApplicationTable items={applications.slice(0, 3)} onSelect={setSelectedApplication} />
              </section>
            </>
          )}

          {page === 'My resumes' && (
            <section>
              <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
                <div><p className="mb-1 text-xs font-semibold uppercase tracking-[0.12em] text-indigo-600">Your documents</p><h2 className="text-[26px] font-bold tracking-tight">My resumes</h2><p className="mt-1 text-sm text-slate-500">Keep tailored versions ready for every opportunity.</p></div>{uploadButton()}
              </div>
              <div className="mb-5 grid gap-4 sm:grid-cols-3"><MiniMetric label="Total resumes" value={String(resumes.length)} icon="file" /><MiniMetric label="Best resume score" value={`${Math.max(...resumes.map((resume) => resume.score)) || 0}/100`} icon="trend" /><MiniMetric label="Last updated" value="Today" icon="clock" /></div>
              <div className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-[0_2px_8px_rgba(15,23,42,.025)]">
                <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4"><div><h3 className="text-sm font-bold">All resumes</h3><p className="mt-1 text-xs text-slate-500">{filteredResumes.length} documents</p></div><label className="flex h-9 items-center gap-2 rounded-lg border border-slate-200 px-3 sm:hidden"><Icon name="search" size={15} className="text-slate-400" /><input aria-label="Search resumes" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search..." className="w-24 bg-transparent text-xs outline-none" /></label></div>
                {filteredResumes.length ? <div className="divide-y divide-slate-100">{filteredResumes.map((resume) => <div key={resume.id} className="flex flex-wrap items-center gap-3 px-5 py-4 transition hover:bg-slate-50/70 sm:flex-nowrap">
                  <div className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${resume.color === 'amber' ? 'bg-amber-50 text-amber-600' : resume.color === 'blue' ? 'bg-blue-50 text-blue-600' : resume.color === 'emerald' ? 'bg-emerald-50 text-emerald-600' : 'bg-violet-50 text-violet-600'}`}><Icon name="file" size={19} /></div>
                  <div className="min-w-0 flex-1"><p className="truncate text-xs font-semibold text-slate-800">{resume.name}</p><p className="mt-1 text-[11px] text-slate-400">{resume.updated} <span className="px-1">·</span> {resume.size}{resume.pageCount ? ` · ${resume.pageCount} pages analyzed` : ''}</p></div>
                  <div className="hidden w-36 sm:block"><div className="mb-1.5 flex justify-between text-[10px]"><span className="text-slate-500">Resume score</span><span className="font-semibold text-slate-700">{resume.score ? `${resume.score}/100` : 'Not analyzed'}</span></div><div className="h-1.5 rounded-full bg-slate-100"><div className={`h-full rounded-full ${resume.score >= 80 ? 'bg-emerald-500' : 'bg-amber-400'}`} style={{ width: `${resume.score}%` }} /></div></div>
                  {resume.pdfFile && <button onClick={() => openResumePdf(resume)} className="rounded-lg border border-slate-200 px-3 py-2 text-[11px] font-semibold text-slate-700 hover:border-indigo-200 hover:text-indigo-700">Open PDF</button>}
                  <button onClick={() => resume.analysis ? setAnalysisResume(resume) : notify('This is sample data. Upload your resume to run AI analysis.')} className="rounded-lg border border-slate-200 px-3 py-2 text-[11px] font-semibold text-slate-700 hover:border-indigo-200 hover:text-indigo-700">{resume.analysis ? 'View analysis' : 'Analyze'}</button>
                  <button aria-label={`Remove ${resume.name}`} onClick={() => { setResumes((items) => items.filter((item) => item.id !== resume.id)); notify('Resume removed from this preview.') }} className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600"><Icon name="close" size={16} /></button>
                </div>)}</div> : <EmptyState title="No resumes found" message="Try another search, or upload a PDF to add a resume." action={uploadButton('Upload a resume', false)} /> }
              </div>
              <p className="mt-4 text-xs text-slate-400">PDF only · Up to 10 MB · Files are not sent to a server in preview mode.</p>
            </section>
          )}

          {page === 'Job tracker' && (
            <section>
              <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="mb-1 text-xs font-semibold uppercase tracking-[0.12em] text-indigo-600">Stay organized</p><h2 className="text-[26px] font-bold tracking-tight">Job tracker</h2><p className="mt-1 text-sm text-slate-500">Every opportunity, all in one place.</p></div><button onClick={() => setNewApplicationOpen(true)} className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700"><Icon name="plus" size={16} />Add application</button></div>
              <div className="mb-5 grid gap-4 sm:grid-cols-3"><MiniMetric label="Total applications" value={String(applications.length)} icon="briefcase" /><MiniMetric label="In progress" value={String(applications.filter((item) => item.status !== 'Rejected').length)} icon="clock" /><MiniMetric label="Interviews" value={String(applications.filter((item) => item.status === 'Interview').length)} icon="calendar" /></div>
              <div className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-[0_2px_8px_rgba(15,23,42,.025)]">
                <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4"><div><h3 className="text-sm font-bold">All applications</h3><p className="mt-1 text-xs text-slate-500">Track your progress and next steps</p></div><label className="flex h-9 items-center gap-2 rounded-lg border border-slate-200 px-3 sm:hidden"><Icon name="search" size={15} className="text-slate-400" /><input aria-label="Search applications" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search..." className="w-24 bg-transparent text-xs outline-none" /></label></div>
                {filteredApplications.length ? <ApplicationTable items={filteredApplications} onStatusChange={updateApplicationStatus} onSelect={setSelectedApplication} /> : <EmptyState title="No applications found" message="Try another search or add an opportunity to your tracker." action={<button onClick={() => setNewApplicationOpen(true)} className="rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white hover:bg-indigo-700">Add application</button>} />}
              </div>
            </section>
          )}

          {page === 'Career profile' && (
            <section className="mx-auto max-w-3xl">
              <div className="mb-6"><p className="mb-1 text-xs font-semibold uppercase tracking-[0.12em] text-indigo-600">Your personal brand</p><h2 className="text-[26px] font-bold tracking-tight">Career profile</h2><p className="mt-1 text-sm text-slate-500">A clear profile helps you stay focused and make a strong first impression.</p></div>
              <div className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-[0_2px_8px_rgba(15,23,42,.025)]">
                <div className="flex items-center gap-4 border-b border-slate-100 px-6 py-6"><div className="grid h-16 w-16 place-items-center rounded-2xl bg-[#f1d4c8] text-lg font-bold text-[#764a40]">AM</div><div><h3 className="font-bold">{profileName}</h3><p className="mt-1 text-sm text-slate-500">{profileRole} · {profileLocation}</p><span className="mt-2 inline-flex rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-semibold text-emerald-700">Open to opportunities</span></div></div>
                <form className="space-y-5 p-6" onSubmit={(event) => { event.preventDefault(); notify('Your profile changes are saved for this preview session.') }}>
                  <div className="grid gap-5 sm:grid-cols-2"><Field label="Full name" value={profileName} onChange={setProfileName} /><Field label="Current / target role" value={profileRole} onChange={setProfileRole} /><Field label="Location" value={profileLocation} onChange={setProfileLocation} /><Field label="Experience level" value="Mid-level · 5 years" onChange={() => undefined} disabled /></div>
                  <div><label htmlFor="profile-summary" className="mb-1.5 block text-xs font-semibold text-slate-700">Professional summary</label><textarea id="profile-summary" defaultValue="Product designer passionate about turning complex problems into simple, thoughtful experiences. Experienced in product strategy, interaction design, and building with cross-functional teams." rows={4} className="w-full resize-y rounded-xl border border-slate-200 px-3.5 py-3 text-sm leading-relaxed text-slate-700 outline-none transition focus:border-indigo-400 focus:ring-4 focus:ring-indigo-50" /></div>
                  <div><p className="mb-2 text-xs font-semibold text-slate-700">Key skills</p><div className="flex flex-wrap gap-2">{['Product design', 'Figma', 'Prototyping', 'User research', 'Design systems', 'Interaction design'].map((skill) => <span key={skill} className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600">{skill}</span>)}</div></div>
                  <div className="flex justify-end border-t border-slate-100 pt-5"><button type="submit" className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700">Save changes</button></div>
                </form>
              </div>
            </section>
          )}
        </main>
        <footer className="px-4 pb-7 text-center text-[10px] text-slate-400 sm:px-7 lg:px-9">CareerAI Preview <span className="px-1">·</span> Demonstration data only</footer>
      </div>

      {toast && <div role="status" className="fixed bottom-5 left-1/2 z-[60] -translate-x-1/2 rounded-xl bg-slate-900 px-4 py-3 text-xs font-medium text-white shadow-xl">{toast}</div>}
      {analysisResume?.analysis && <ResumeAnalysisDialog resume={analysisResume} onClose={() => setAnalysisResume(null)} />}
      {selectedApplication && <ApplicationDialog application={selectedApplication} onClose={() => setSelectedApplication(null)} onStatusChange={updateApplicationStatus} />}
      {newApplicationOpen && <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/40 p-4" onMouseDown={(event) => { if (event.target === event.currentTarget) setNewApplicationOpen(false) }}><form onSubmit={createApplication} className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl"><div className="mb-5 flex items-start justify-between"><div><h2 className="text-lg font-bold">Add an application</h2><p className="mt-1 text-xs text-slate-500">Keep track of a new opportunity.</p></div><button type="button" aria-label="Close dialog" onClick={() => setNewApplicationOpen(false)} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100"><Icon name="close" /></button></div><div className="space-y-4"><Field label="Job title" value={newRole} onChange={setNewRole} placeholder="e.g. Product Designer" required /><Field label="Company" value={newCompany} onChange={setNewCompany} placeholder="e.g. Acme Inc." required /></div><div className="mt-6 flex justify-end gap-2"><button type="button" onClick={() => setNewApplicationOpen(false)} className="rounded-xl border border-slate-200 px-4 py-2.5 text-xs font-semibold text-slate-600 hover:bg-slate-50">Cancel</button><button type="submit" className="rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white hover:bg-indigo-700">Add application</button></div></form></div>}
    </div>
  )
}

function StatCard({ icon, title, value, suffix, trend, color }: { icon: string; title: string; value: string; suffix?: string; trend: string; color: string }) {
  const styles: Record<string, string> = { indigo: 'bg-indigo-50 text-indigo-600', amber: 'bg-amber-50 text-amber-600', emerald: 'bg-emerald-50 text-emerald-600', violet: 'bg-violet-50 text-violet-600' }
  return <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_2px_8px_rgba(15,23,42,.025)]"><div className="flex items-center justify-between"><span className="text-xs font-medium text-slate-500">{title}</span><span className={`grid h-9 w-9 place-items-center rounded-xl ${styles[color]}`}><Icon name={icon} size={18} /></span></div><div className="mt-3 flex items-baseline gap-1"><span className="text-[27px] font-bold tracking-tight">{value}</span>{suffix && <span className="text-xs font-medium text-slate-400">{suffix}</span>}</div><div className="mt-2 flex items-center gap-1.5 text-[10px] font-medium text-emerald-600"><Icon name="trend" size={13} />{trend}</div></div>
}

function MiniMetric({ label, value, icon }: { label: string; value: string; icon: string }) {
  return <div className="flex items-center gap-3 rounded-2xl border border-slate-200/80 bg-white p-4 shadow-[0_2px_8px_rgba(15,23,42,.025)]"><span className="grid h-9 w-9 place-items-center rounded-xl bg-indigo-50 text-indigo-600"><Icon name={icon} size={17} /></span><div><p className="text-[11px] text-slate-500">{label}</p><p className="mt-0.5 text-sm font-bold">{value}</p></div></div>
}

function ApplicationTable({ items, onStatusChange, onSelect }: { items: Application[]; onStatusChange?: (id: number, status: string) => void; onSelect: (application: Application) => void }) {
  return <div className="overflow-x-auto"><table className="w-full min-w-[570px] text-left"><thead className="bg-slate-50/70 text-[10px] font-semibold uppercase tracking-wide text-slate-400"><tr><th className="px-5 py-3">Position</th><th className="px-4 py-3">Date applied</th><th className="px-4 py-3">Status</th><th className="px-5 py-3 text-right">Action</th></tr></thead><tbody className="divide-y divide-slate-100">{items.map((item) => <tr key={item.id} className="hover:bg-slate-50/50"><td className="px-5 py-3.5"><div className="flex items-center gap-3"><div className={`grid h-9 w-9 shrink-0 place-items-center rounded-lg text-[10px] font-bold ${item.color === 'violet' ? 'bg-violet-100 text-violet-700' : item.color === 'amber' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'}`}>{item.company.slice(0, 2).toUpperCase()}</div><div><p className="text-xs font-semibold text-slate-800">{item.role}</p><p className="mt-0.5 text-[10px] text-slate-400">{item.company}</p></div></div></td><td className="px-4 py-3.5 text-[11px] text-slate-500">{item.date}</td><td className="px-4 py-3.5">{onStatusChange ? <select aria-label={`Status for ${item.company}`} value={item.status} onChange={(event) => onStatusChange(item.id, event.target.value)} className="cursor-pointer border-0 bg-transparent p-0 outline-none"><option>Applied</option><option>In review</option><option>Interview</option><option>Rejected</option><option>Offer</option></select> : <StatusBadge status={item.status} />}</td><td className="px-5 py-3.5 text-right"><button onClick={() => onSelect(item)} aria-label={`View ${item.company} application`} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"><Icon name="arrow" size={15} /></button></td></tr>)}</tbody></table></div>
}

function EmptyState({ title, message, action }: { title: string; message: string; action: ReactNode }) {
  return <div className="flex flex-col items-center px-6 py-14 text-center"><div className="mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-slate-100 text-slate-500"><Icon name="search" size={21} /></div><h4 className="text-sm font-semibold">{title}</h4><p className="mt-1 max-w-xs text-xs leading-relaxed text-slate-500">{message}</p><div className="mt-4">{action}</div></div>
}

function Field({ label, value, onChange, placeholder, required, disabled }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string; required?: boolean; disabled?: boolean }) {
  const inputId = label.toLowerCase().replace(/[^a-z0-9]+/g, '-')
  return <div><label htmlFor={inputId} className="mb-1.5 block text-xs font-semibold text-slate-700">{label}</label><input id={inputId} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} required={required} disabled={disabled} className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-indigo-400 focus:ring-4 focus:ring-indigo-50 disabled:bg-slate-50 disabled:text-slate-400" /></div>
}

function ResumeAnalysisDialog({ resume, onClose }: { resume: Resume; onClose: () => void }) {
  if (!resume.analysis) return null
  return <div role="presentation" className="fixed inset-0 z-50 grid place-items-center bg-slate-950/40 p-4" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><section role="dialog" aria-modal="true" aria-labelledby="resume-analysis-title" className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white shadow-2xl"><div className="sticky top-0 z-10 flex items-center justify-between gap-4 border-b border-slate-100 bg-white px-5 py-4"><div className="min-w-0"><p className="text-[10px] font-semibold uppercase tracking-wider text-indigo-600">AI resume analysis · {resume.pageCount} pages</p><h2 id="resume-analysis-title" className="mt-1 truncate text-sm font-bold">{resume.name}</h2></div><button aria-label="Close resume analysis" onClick={onClose} className="shrink-0 rounded-lg p-2 text-slate-400 hover:bg-slate-100"><Icon name="close" /></button></div><ResumeAnalysisView state={{ status: 'ready', result: resume.analysis }} /><div className="flex justify-end border-t border-slate-100 px-5 py-4"><button onClick={onClose} className="rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white hover:bg-indigo-700">Done</button></div></section></div>
}

function ApplicationDialog({ application, onClose, onStatusChange }: { application: Application; onClose: () => void; onStatusChange: (id: number, status: string) => void }) {
  return <div role="presentation" className="fixed inset-0 z-50 grid place-items-center bg-slate-950/40 p-4" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><section role="dialog" aria-modal="true" aria-labelledby="application-title" className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl"><div className="flex items-start justify-between"><div><p className="text-[10px] font-semibold uppercase tracking-wider text-indigo-600">Application details</p><h2 id="application-title" className="mt-1 text-lg font-bold">{application.role}</h2><p className="mt-1 text-sm text-slate-500">{application.company}</p></div><button aria-label="Close application details" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100"><Icon name="close" /></button></div><dl className="mt-5 space-y-4 border-t border-slate-100 pt-5"><div><dt className="text-[10px] font-semibold uppercase text-slate-400">Date added</dt><dd className="mt-1 text-sm text-slate-700">{application.date}</dd></div><div><label htmlFor="application-status" className="text-[10px] font-semibold uppercase text-slate-400">Application status</label><select id="application-status" value={application.status} onChange={(event) => onStatusChange(application.id, event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 outline-none focus:border-indigo-400"><option>Applied</option><option>In review</option><option>Interview</option><option>Rejected</option><option>Offer</option></select></div></dl><div className="mt-6 flex justify-end"><button onClick={onClose} className="rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white hover:bg-indigo-700">Done</button></div></section></div>
}

export default App
