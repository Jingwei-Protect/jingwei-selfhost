import { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import jingweiLogo from '../assets/jingwei-logo.png'
import { useLocale } from '../i18n/LocaleContext'
import LanguageSwitcher from '../i18n/LanguageSwitcher'
import { useAdvProtectEnabled } from '../hooks/useAdvProtectEnabled'

export default function SiteNav() {
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()
  const { messages: m } = useLocale()
  const n = m.common.nav
  const advOn = useAdvProtectEnabled()

  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  useEffect(() => {
    document.body.classList.toggle('nav-drawer-open', menuOpen)
    return () => document.body.classList.remove('nav-drawer-open')
  }, [menuOpen])

  return (
    <nav className="nav">
      <div className="nav-inner">
        <NavLink to="/" end className="nav-brand" aria-label={m.common.siteName} onClick={() => setMenuOpen(false)}>
          <img src={jingweiLogo} alt={m.common.siteName} className="jingwei-logo" />
        </NavLink>
        <button
          type="button"
          className="nav-menu-toggle"
          aria-expanded={menuOpen}
          aria-controls="site-nav-links"
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? n.close : n.menu}
        </button>
        <div id="site-nav-links" className={`nav-links${menuOpen ? ' is-open' : ''}`}>
          <NavLink to="/" end className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
            {n.about}
          </NavLink>
          <NavLink to="/protect" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
            {n.protect}
          </NavLink>
          <NavLink to="/verify" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
            {n.verify}
          </NavLink>
          {advOn && (
            <NavLink to="/adv-protect" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
              AdvProtect
            </NavLink>
          )}
          <NavLink to="/protocol" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
            {n.protocol}
          </NavLink>
          <LanguageSwitcher />
        </div>
      </div>
      {menuOpen && (
        <button
          type="button"
          className="nav-drawer-backdrop"
          aria-label={n.closeMenu}
          onClick={() => setMenuOpen(false)}
        />
      )}
    </nav>
  )
}
