/**
 * ArogyaMitra Authentication & Session Controller
 * Source of truth: User Requirements 4-10, 12, 13, 14, 15, 16
 */

const AuthController = {
  selectedRole: null,
  pendingStaffLoginId: null,

  init() {
    // Check if session is already stored in sessionStorage
    const savedUser = sessionStorage.getItem('arogya_user');
    if (savedUser) {
      try {
        const user = JSON.parse(savedUser);
        this.setUserSession(user, false);
      } catch (e) {
        this.clearSession();
      }
    }
  },

  selectRole(role) {
    this.selectedRole = role;
    if (role === 'PATIENT') {
      this.openPatientAuthModal('login');
    } else {
      this.openStaffLoginModal(role);
    }
  },

  openPatientAuthModal(tab = 'login') {
    const modal = document.getElementById('patient-auth-modal');
    if (!modal) return;
    modal.classList.remove('hidden');
    this.switchPatientTab(tab);
    if (window.lucide) window.lucide.createIcons();
  },

  closePatientAuthModal() {
    const modal = document.getElementById('patient-auth-modal');
    if (modal) modal.classList.add('hidden');
  },

  switchPatientTab(tab) {
    const tabLogin = document.getElementById('pat-tab-btn-login');
    const tabReg = document.getElementById('pat-tab-btn-reg');
    const formLogin = document.getElementById('pat-form-login');
    const formReg = document.getElementById('pat-form-reg');

    if (tab === 'login') {
      if (tabLogin) tabLogin.className = 'flex-1 py-2.5 text-center font-bold text-xs sm:text-sm border-b-2 border-[#7CA68D] text-[#7CA68D]';
      if (tabReg) tabReg.className = 'flex-1 py-2.5 text-center font-semibold text-xs sm:text-sm border-b-2 border-transparent text-slate-500 hover:text-slate-800';
      if (formLogin) formLogin.classList.remove('hidden');
      if (formReg) formReg.classList.add('hidden');
    } else {
      if (tabReg) tabReg.className = 'flex-1 py-2.5 text-center font-bold text-xs sm:text-sm border-b-2 border-[#7CA68D] text-[#7CA68D]';
      if (tabLogin) tabLogin.className = 'flex-1 py-2.5 text-center font-semibold text-xs sm:text-sm border-b-2 border-transparent text-slate-500 hover:text-slate-800';
      if (formReg) formReg.classList.remove('hidden');
      if (formLogin) formLogin.classList.add('hidden');
    }
  },

  async handlePatientLogin(e) {
    if (e) e.preventDefault();
    const loginId = document.getElementById('pat-login-id')?.value.trim();
    const password = document.getElementById('pat-login-password')?.value;

    if (!loginId || !password) {
      App.showToast('Please enter your Phone/ABHA and password.', 'warning');
      return;
    }

    try {
      const res = await fetch('/api/auth/patient/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ login_id: loginId, password: password })
      });
      const data = await res.json();
      if (!res.ok) {
        App.showToast(data.detail || 'Login failed', 'warning');
        return;
      }

      this.closePatientAuthModal();
      this.setUserSession(data.user);
      App.activePatient = data.patient;
      App.activeConsultationId = data.consultation_id;
      // Fetch full patient profile to obtain latest consent and persistent language
      try {
        const profileRes = await fetch(`/api/patient/${App.activePatient.patient_id}`);
        const profileData = await profileRes.json();
        if (profileData && profileData.patient) {
          App.activePatient = profileData.patient;
          App.currentLanguage = App.activePatient.preferred_language || data.user.preferred_language || 'en';
        } else {
          App.currentLanguage = data.user.preferred_language || 'en';
        }
      } catch (err) {
        App.currentLanguage = data.user.preferred_language || 'en';
      }

      App.showToast(`Welcome back, ${data.user.full_name}!`);
      App.enterRoleView('PATIENT');
    } catch (err) {
      App.showToast('Network error during patient login.', 'warning');
    }
  },

  async handlePatientRegister(e) {
    if (e) e.preventDefault();
    const name = document.getElementById('pat-reg-name')?.value.trim();
    const phone = document.getElementById('pat-reg-phone')?.value.trim();
    const password = document.getElementById('pat-reg-password')?.value;
    const dob = document.getElementById('pat-reg-dob')?.value || '1985-01-01';
    const gender = document.getElementById('pat-reg-gender')?.value || 'Male';
    const abhaId = document.getElementById('pat-reg-abha')?.value.trim();
    const language = document.getElementById('pat-reg-lang')?.value || 'en';

    if (!name || !phone || !password) {
      App.showToast('Please provide Name, Phone Number, and Password.', 'warning');
      return;
    }

    try {
      const res = await fetch('/api/auth/patient/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name,
          phone: phone,
          password: password,
          date_of_birth: dob,
          gender: gender,
          abha_id: abhaId,
          preferred_language: language
        })
      });
      const data = await res.json();
      if (!res.ok) {
        App.showToast(data.detail || 'Registration failed', 'warning');
        return;
      }

      this.closePatientAuthModal();
      this.setUserSession(data.user);
      App.activePatient = data.patient;
      App.activeConsultationId = data.consultation_id;
      App.currentLanguage = language;

      App.showToast(`Account created! Welcome, ${name}. Token: ${data.token_code}`);
      App.enterRoleView('PATIENT');
    } catch (err) {
      App.showToast('Network error during registration.', 'warning');
    }
  },

  openStaffLoginModal(role = 'DOCTOR') {
    this.selectedRole = role;
    const modal = document.getElementById('staff-login-modal');
    const roleBadge = document.getElementById('staff-login-role-badge');
    const roleTitle = document.getElementById('staff-login-title');

    if (roleBadge) {
      roleBadge.innerText = role;
      if (role === 'DOCTOR') roleBadge.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-100 text-blue-800';
      if (role === 'RADIOLOGIST') roleBadge.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-100 text-purple-800';
      if (role === 'ADMIN') roleBadge.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800';
    }
    if (roleTitle) roleTitle.innerText = `${role.charAt(0) + role.slice(1).toLowerCase()} Portal Login`;

    // Staff credentials must be entered by authorized users; no autofill provided.

    if (modal) modal.classList.remove('hidden');
    if (window.lucide) window.lucide.createIcons();
  },

  closeStaffLoginModal() {
    const modal = document.getElementById('staff-login-modal');
    if (modal) modal.classList.add('hidden');
  },

  async handleStaffLogin(e) {
    if (e) e.preventDefault();
    const loginId = document.getElementById('staff-login-id')?.value.trim();
    const password = document.getElementById('staff-login-password')?.value;

    if (!loginId || !password) {
      App.showToast('Please enter your Login ID and Password.', 'warning');
      return;
    }

    try {
      const res = await fetch('/api/auth/staff/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          login_id: loginId,
          password: password,
          expected_role: this.selectedRole
        })
      });
      const data = await res.json();
      if (!res.ok) {
        App.showToast(data.detail || 'Login failed', 'warning');
        return;
      }

      this.closeStaffLoginModal();

      // Check if user must change temporary password
      if (data.must_change_password) {
        this.pendingStaffLoginId = loginId;
        this.openForcePasswordModal(loginId, data.user.full_name);
        return;
      }

      this.setUserSession(data.user);
      // Apply saved preferred language if present
      if (data.user.preferred_language) {
        App.currentLanguage = data.user.preferred_language;
        VoiceEngine.setLanguage(App.currentLanguage);
      } else {
        // Ask user to pick a preferred language on first login
        const pick = window.prompt('Select preferred language code (e.g. en, hi, bn, te, ta):', 'en');
        if (pick) {
          try {
            await fetch('/api/auth/staff/set-language', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ staff_id: data.user.staff_id, preferred_language: pick })
            });
            App.currentLanguage = pick;
            VoiceEngine.setLanguage(App.currentLanguage);
          } catch (err) {
            console.error('Failed to save staff language preference:', err);
          }
        }
      }

      App.showToast(`Logged in as ${data.user.full_name} (${data.user.role})`);
      App.enterRoleView(data.user.role);
    } catch (err) {
      App.showToast('Network error during staff login.', 'warning');
    }
  },

  openForcePasswordModal(loginId, fullName) {
    const modal = document.getElementById('force-password-modal');
    const userLabel = document.getElementById('force-pwd-user-label');
    if (userLabel) userLabel.innerText = `${fullName} (${loginId})`;
    if (modal) modal.classList.remove('hidden');
  },

  togglePassword(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    if (input.type === 'password') {
      input.type = 'text';
      if (btn) btn.innerText = 'Hide';
    } else {
      input.type = 'password';
      if (btn) btn.innerText = 'Show';
    }
  },

  closeForcePasswordModal() {
    const modal = document.getElementById('force-password-modal');
    if (modal) modal.classList.add('hidden');
  },

  async handleForcePasswordChange(e) {
    if (e) e.preventDefault();
    const oldPassword = document.getElementById('force-pwd-old')?.value;
    const newPassword = document.getElementById('force-pwd-new')?.value;
    const confirmPassword = document.getElementById('force-pwd-confirm')?.value;

    if (!oldPassword || !newPassword || !confirmPassword) {
      App.showToast('Please fill all password fields.', 'warning');
      return;
    }

    if (newPassword !== confirmPassword) {
      App.showToast('New passwords do not match.', 'warning');
      return;
    }

    try {
      const res = await fetch('/api/auth/staff/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          login_id: this.pendingStaffLoginId,
          old_password: oldPassword,
          new_password: newPassword,
          confirm_password: confirmPassword
        })
      });
      const data = await res.json();
      if (!res.ok) {
        App.showToast(data.detail || 'Password update failed', 'warning');
        return;
      }

      this.closeForcePasswordModal();
      App.showToast('Password updated! Please log in with your new password.', 'success');
      this.openStaffLoginModal(this.selectedRole || 'ADMIN');
    } catch (err) {
      App.showToast('Failed to update password.', 'warning');
    }
  },

  setUserSession(user, save = true) {
    App.currentUser = user;
    if (save) {
      sessionStorage.setItem('arogya_user', JSON.stringify(user));
    }
    this.renderUserBadge(user);
  },

  renderUserBadge(user) {
    const userBadgeContainer = document.getElementById('header-user-badge');
    if (!userBadgeContainer) return;

    if (!user) {
      userBadgeContainer.innerHTML = '';
      return;
    }

    userBadgeContainer.innerHTML = `
      <div class="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-100 border border-slate-200 text-xs">
        <div class="w-6 h-6 rounded-full bg-[#7CA68D] text-white flex items-center justify-center text-[10px] font-bold">
          ${user.full_name ? user.full_name.charAt(0) : 'U'}
        </div>
        <div class="leading-tight text-left">
          <div class="font-bold text-slate-800 truncate max-w-[140px]">${user.full_name || user.name || 'User'}</div>
          <div class="text-[10px] text-slate-500 font-semibold">${user.role}</div>
        </div>
        <button onclick="AuthController.logout()" class="ml-1 p-1 rounded hover:bg-slate-200 text-slate-500 hover:text-red-600 transition" title="Logout session">
          <i data-lucide="log-out" class="w-3.5 h-3.5"></i>
        </button>
      </div>
    `;
    if (window.lucide) window.lucide.createIcons();
  },

  async logout() {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
    } catch (e) {}
    this.clearSession();
    App.showToast('Session terminated.');
    App.showLandingScreen();
  },

  clearSession() {
    App.currentUser = null;
    App.activePatient = null;
    App.activeConsultationId = null;
    sessionStorage.removeItem('arogya_user');
    this.renderUserBadge(null);
  }
};

window.AuthController = AuthController;
