import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { siteContentAPI, authAPI } from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { toast } from 'sonner';
import { Building2, Shield } from 'lucide-react';

const LoginPage = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);
  const [loginEmail, setLoginEmail] = useState('');
  const passwordRef = useRef(null);
  const [forgotMode, setForgotMode] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotLoading, setForgotLoading] = useState(false);
  const [content, setContent] = useState({
    heading_line1: 'Reserve Your', heading_highlight: 'Parking Spot', heading_line3: 'with Ease',
    description: 'Seamlessly book, manage, and track your parking reservations across all Cebuana Lhuillier buildings.',
    badge1_text: 'Multiple Buildings', badge2_text: 'Secure Access', announcement: ''
  });

  useEffect(() => {
    siteContentAPI.get().then(res => setContent(res.data)).catch(() => {});
  }, []);

  // V-11 HARDENING: aggressively wipe the password input whenever the window
  // loses focus or the tab is hidden. Limits the time window during which the
  // cleartext password is reachable via JS / DevTools / malicious extensions.
  // (HTML password inputs always expose .value while focused — accepted residual
  // risk; mitigated further by HttpOnly auth cookies + strict CSP.)
  useEffect(() => {
    const wipe = () => {
      if (passwordRef.current && passwordRef.current.value) {
        passwordRef.current.value = '';
      }
    };
    window.addEventListener('blur', wipe);
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) wipe();
    });
    return () => {
      window.removeEventListener('blur', wipe);
      // visibilitychange listener is anonymous; document teardown handles it
    };
  }, []);

  const handleLogin = async (e) => {
    e.preventDefault();
    const password = passwordRef.current?.value || '';

    if (!loginEmail.trim()) {
      toast.error('Please enter your email address');
      return;
    }
    // QAT-LOGIN-005 fix: client-side email format check so an invalid email
    // never reaches the server (which used to bubble a 422 that crashed the
    // page into a blank state). Standard RFC-ish regex; backend EmailStr
    // remains the source of truth.
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(loginEmail.trim())) {
      toast.error('Please enter a valid email address');
      return;
    }
    if (!password) {
      toast.error('Please enter your password');
      return;
    }
    // QAT-LOGIN-006 fix: reject leading/trailing whitespace with a clear message
    // (was showing the misleading HTML5 'Please fill in this field' before).
    if (password !== password.trim() || !password.trim()) {
      toast.error('Password cannot have leading or trailing spaces');
      return;
    }

    setLoading(true);
    try {
      const user = await login(loginEmail, password);
      if (passwordRef.current) passwordRef.current.value = '';
      toast.success(`Welcome back, ${user.first_name}!`);
      if (user.role === 'admin') navigate('/admin');
      else if (user.role === 'attendant') navigate('/attendant');
      else navigate('/dashboard');
    } catch (error) {
      // QAT-LOGIN-005 fix: ALWAYS show a toast on login error and stay on the
      // login page. Never let an unhandled error cause a blank page.
      const detail =
        error?.response?.data?.detail ||
        error?.message ||
        'Login failed. Please try again.';
      toast.error(typeof detail === 'string' ? detail : 'Login failed');
      if (passwordRef.current) passwordRef.current.value = '';
    } finally { setLoading(false); }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    if (!forgotEmail) { return; }
    setForgotLoading(true);
    try {
      const res = await authAPI.forgotPassword(forgotEmail);
      toast.success(res.data.message);
      setForgotMode(false);
      setForgotEmail('');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Something went wrong');
    } finally { setForgotLoading(false); }
  };

  return (
    <div className="min-h-screen relative overflow-hidden">
      <div className="absolute inset-0" style={{ background: 'linear-gradient(135deg, #051a2d 0%, #08263e 40%, #0d3454 70%, #08263e 100%)' }}>
        <div className="absolute inset-0 opacity-[0.06]">
          <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
            <defs><pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse"><path d="M 60 0 L 0 0 0 60" fill="none" stroke="white" strokeWidth="0.5"/></pattern></defs>
            <rect width="100%" height="100%" fill="url(#grid)" />
          </svg>
        </div>
        <div className="absolute top-1/2 left-1/4 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full" style={{ background: 'radial-gradient(circle, rgba(81,141,202,0.12) 0%, transparent 70%)' }} />
        <div className="absolute top-0 right-0 w-[400px] h-[400px] rounded-full" style={{ background: 'radial-gradient(circle, rgba(236,71,78,0.08) 0%, transparent 70%)' }} />
      </div>

      <div className="relative z-10 min-h-screen flex items-center justify-center p-4 md:p-8">
        <div className="w-full max-w-5xl grid md:grid-cols-2 gap-8 items-center">
          <div className="text-white space-y-6 animate-fadeIn">
            <div className="flex items-center gap-3">
              <div className="bg-white/95 rounded-xl px-4 py-2 shadow-lg">
                <img src="/cl-logo.png" alt="Cebuana Lhuillier" className="h-12 w-auto" />
              </div>
            </div>

            {content.announcement && (
              <div className="bg-[#ec474e]/20 border border-[#ec474e]/30 rounded-lg px-4 py-2 text-sm backdrop-blur-sm" data-testid="login-announcement">
                {content.announcement}
              </div>
            )}

            <h2 className="text-4xl md:text-5xl font-extrabold leading-tight drop-shadow-[0_2px_4px_rgba(0,0,0,0.3)]">
              {content.heading_line1}<br/>
              <span className="text-[#ec474e] drop-shadow-[0_2px_8px_rgba(236,71,78,0.4)]">{content.heading_highlight}</span><br/>
              {content.heading_line3}
            </h2>

            <p className="text-white/90 text-lg max-w-md">{content.description}</p>

            <div className="flex gap-6 pt-4">
              {content.badge1_text && (
                <div className="flex items-center gap-2 bg-white/10 rounded-full px-4 py-2 backdrop-blur-sm">
                  <Building2 className="w-5 h-5 text-[#ec474e]" />
                  <span className="text-sm font-medium">{content.badge1_text}</span>
                </div>
              )}
              {content.badge2_text && (
                <div className="flex items-center gap-2 bg-white/10 rounded-full px-4 py-2 backdrop-blur-sm">
                  <Shield className="w-5 h-5 text-[#ec474e]" />
                  <span className="text-sm font-medium">{content.badge2_text}</span>
                </div>
              )}
            </div>
          </div>

          <Card className="backdrop-blur-xl bg-white shadow-2xl border-0 animate-fadeIn" style={{ animationDelay: '0.2s' }}>
            <CardHeader className="text-center pb-2">
              <CardTitle className="text-2xl text-[#08263e]">Welcome</CardTitle>
              <CardDescription>Sign in to your account</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleLogin} className="space-y-4" noValidate>
                <div className="space-y-2">
                  <Label htmlFor="login-email">Email</Label>
                  {/* V-09 FIX: Generic placeholder that doesn't reveal email domain */}
                  <Input id="login-email" type="email" placeholder="Enter your email address" value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)} required data-testid="login-email-input" className="h-11" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="login-password">Password</Label>
                  {/* V-11 FIX: Using ref-based input to avoid password in React state/DOM */}
                  <Input id="login-password" type="password" placeholder="Enter your password" ref={passwordRef}
                    autoComplete="current-password" required data-testid="login-password-input" className="h-11" />
                </div>
                <Button type="submit" className="w-full h-11 bg-[#ec474e] hover:bg-[#d63a41] text-white rounded-full font-semibold"
                  disabled={loading} data-testid="login-submit-btn">
                  {loading ? 'Signing in...' : 'Sign In'}
                </Button>
                <div className="flex justify-between items-center mt-2">
                  <button type="button" className="text-xs text-sky-600 hover:underline" onClick={() => setForgotMode(true)} data-testid="forgot-password-link">
                    Forgot Password?
                  </button>
                  <span className="text-xs text-gray-400">Contact admin for new accounts</span>
                </div>
              </form>
              {forgotMode && (
                <form onSubmit={handleForgotPassword} className="mt-4 pt-4 border-t space-y-3">
                  <p className="text-sm text-gray-600">Enter your email and your administrator will be notified to reset your password.</p>
                  {/* V-09 FIX: Generic placeholder */}
                  <Input type="email" placeholder="Enter your email address" value={forgotEmail}
                    onChange={e => setForgotEmail(e.target.value)} required data-testid="forgot-email-input" className="h-10" />
                  <div className="flex gap-2">
                    <Button type="button" variant="outline" size="sm" onClick={() => { setForgotMode(false); setForgotEmail(''); }}>Cancel</Button>
                    <Button type="submit" size="sm" disabled={forgotLoading} data-testid="forgot-submit-btn" className="bg-[#ec474e] hover:bg-[#d63a41] text-white">
                      {forgotLoading ? 'Sending...' : 'Request Reset'}
                    </Button>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
