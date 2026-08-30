import I18nSeoHead from './components/I18nSeoHead'
import { CONTACT_EMAIL } from './lib/site'
import { NavLink, Route, Routes } from 'react-router-dom'
import SiteNav from './components/SiteNav'
import WigglyDefs from './components/nameplate/WigglyDefs'
import HomePage from './pages/HomePage'
import ProtectPage from './pages/ProtectPage'
import VerifyPage from './pages/VerifyPage'
import AdvProtectPage from './pages/AdvProtectPage'
import JingweiProtocolPage from './pages/JingweiProtocolPage'
import PrivacyPage from './pages/PrivacyPage'
import TermsPage from './pages/TermsPage'
import GuideMatrixPage from './pages/GuideMatrixPage'
import { useLocale } from './i18n/LocaleContext'

function AppFooter() {
  const { messages: m } = useLocale()
  const f = m.common.footer
  return (
    <footer className="footer">
      <div className="container">
        <p>{f.tagline}</p>
        <p className="text-sm" style={{ marginTop: 'var(--space-1)', opacity: 0.55 }}>
          Self-host · official site{' '}
          <a href="https://jwprotect.com">jwprotect.com</a>
        </p>
        <p className="text-sm" style={{ marginTop: 'var(--space-2)', opacity: 0.6 }}>
          <NavLink to="/privacy" style={{ marginRight: 12 }}>{f.privacy}</NavLink>
          <NavLink to="/terms" style={{ marginRight: 12 }}>{f.terms}</NavLink>
          <NavLink to="/protocol" style={{ marginRight: 12 }}>{f.protocol}</NavLink>
          <NavLink to="/guide/watermark-matrix" style={{ marginRight: 12 }}>{f.matrix}</NavLink>
          {f.contactLabel}：{CONTACT_EMAIL}
        </p>
      </div>
    </footer>
  )
}

function AppShell() {
  return (
    <>
      <I18nSeoHead />
      <WigglyDefs />
      <SiteNav />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/protect" element={<ProtectPage />} />
        <Route path="/verify" element={<VerifyPage />} />
        <Route path="/adv-protect" element={<AdvProtectPage />} />
        <Route path="/protocol" element={<JingweiProtocolPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/guide/watermark-matrix" element={<GuideMatrixPage />} />
      </Routes>
      <AppFooter />
    </>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/*" element={<AppShell />} />
    </Routes>
  )
}
