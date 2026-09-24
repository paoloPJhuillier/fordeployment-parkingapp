import React, { useState, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { Lock, Eye, EyeOff } from 'lucide-react';

export default function ForcePasswordChange() {
  const { completePasswordChange, logout } = useAuth();
  const newPasswordRef = useRef(null);
  const confirmPasswordRef = useRef(null);
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  // Track only validation flags, never the plaintext password
  const [strength, setStrength] = useState({ len: false, upper: false, lower: false, digit: false });

  const onPasswordInput = () => {
    const val = newPasswordRef.current?.value || '';
    setStrength({ len: val.length >= 8, upper: /[A-Z]/.test(val), lower: /[a-z]/.test(val), digit: /[0-9]/.test(val) });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const pw = newPasswordRef.current?.value || '';
    const cpw = confirmPasswordRef.current?.value || '';
    if (pw.length < 8) { toast.error('Password must be at least 8 characters'); return; }
    if (!/[A-Z]/.test(pw)) { toast.error('Password must contain an uppercase letter'); return; }
    if (!/[a-z]/.test(pw)) { toast.error('Password must contain a lowercase letter'); return; }
    if (!/[0-9]/.test(pw)) { toast.error('Password must contain a digit'); return; }
    if (pw !== cpw) { toast.error('Passwords do not match'); return; }

    setSubmitting(true);
    try {
      await completePasswordChange(pw);
      if (newPasswordRef.current) newPasswordRef.current.value = '';
      if (confirmPasswordRef.current) confirmPasswordRef.current.value = '';
      setStrength({ len: false, upper: false, lower: false, digit: false });
      toast.success('Password changed successfully!');
    } catch (error) {
      if (newPasswordRef.current) newPasswordRef.current.value = '';
      if (confirmPasswordRef.current) confirmPasswordRef.current.value = '';
      setStrength({ len: false, upper: false, lower: false, digit: false });
      toast.error(error.response?.data?.detail || 'Failed to change password');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: 'linear-gradient(135deg, #051a2d 0%, #08263e 40%, #0d3454 70%, #08263e 100%)' }} data-testid="force-password-change">
      <Card className="w-full max-w-md shadow-2xl border-0">
        <CardHeader className="text-center pb-2">
          <div className="mx-auto w-14 h-14 rounded-full bg-[#ec474e]/10 flex items-center justify-center mb-3">
            <Lock className="w-7 h-7 text-[#ec474e]" />
          </div>
          <CardTitle className="text-xl text-[#08263e]">Create Your New Password</CardTitle>
          <p className="text-sm text-gray-500 mt-1">Your account requires a password change before you can continue.</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="new-password">New Password</Label>
              <div className="relative">
                <Input
                  id="new-password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter new password"
                  ref={newPasswordRef}
                  onChange={onPasswordInput}
                  autoComplete="new-password"
                  required
                  data-testid="new-password-input"
                />
                <button type="button" className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600" onClick={() => setShowPassword(!showPassword)}>
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm-password">Confirm Password</Label>
              <Input
                id="confirm-password"
                type={showPassword ? 'text' : 'password'}
                placeholder="Confirm new password"
                ref={confirmPasswordRef}
                autoComplete="new-password"
                required
                data-testid="confirm-password-input"
              />
            </div>
            <ul className="text-xs text-gray-500 space-y-1 pl-4 list-disc">
              <li className={strength.len ? 'text-emerald-600' : ''}>At least 8 characters</li>
              <li className={strength.upper ? 'text-emerald-600' : ''}>One uppercase letter</li>
              <li className={strength.lower ? 'text-emerald-600' : ''}>One lowercase letter</li>
              <li className={strength.digit ? 'text-emerald-600' : ''}>One digit</li>
            </ul>
            <Button type="submit" className="w-full bg-[#08263e] hover:bg-[#051a2d] text-white" disabled={submitting} data-testid="change-password-submit-btn">
              {submitting ? 'Changing...' : 'Set New Password'}
            </Button>
            <Button type="button" variant="ghost" className="w-full text-gray-500" onClick={logout} data-testid="change-password-logout-btn">
              Sign Out
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
