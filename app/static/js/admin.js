/**
 * ArogyaMitra Administration & Account Management Controller
 * Source of truth: User Requirements 8, 9, 10 & systemdesign.md Section 14
 */

const AdminPortal = {
  lastGeneratedCredentials: null,

  async init() {
    await this.loadConfig();
    await this.loadAuditLogs();
    await this.loadStaffAccounts();
  },

  async loadConfig() {
    try {
      const res = await fetch('/api/admin/config');
      const data = await res.json();
      const config = data.config || {};

      const ayushToggle = document.getElementById('config-ayush-toggle');
      const abdmToggle = document.getElementById('config-abdm-toggle');
      const retentionInput = document.getElementById('config-retention-input');

      if (ayushToggle) ayushToggle.checked = config.ayush_mode === 'true';
      if (abdmToggle) abdmToggle.checked = config.mock_abdm === 'true';
      if (retentionInput) retentionInput.value = config.retention_policy_days || 30;
    } catch (err) {
      console.error('Failed to load system config:', err);
    }
  },

  async saveConfig() {
    const ayushToggle = document.getElementById('config-ayush-toggle');
    const abdmToggle = document.getElementById('config-abdm-toggle');
    const retentionInput = document.getElementById('config-retention-input');

    try {
      const res = await fetch('/api/admin/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ayush_mode: ayushToggle ? ayushToggle.checked : true,
          mock_abdm: abdmToggle ? abdmToggle.checked : true,
          retention_days: retentionInput ? parseInt(retentionInput.value) : 30
        })
      });
      const data = await res.json();
      if (data.success) {
        App.showToast('System operational configuration updated.');
        this.loadAuditLogs();
      }
    } catch (err) {
      console.error('Failed to save config:', err);
    }
  },

  async loadAuditLogs() {
    try {
      const res = await fetch('/api/admin/audit-logs?limit=50');
      const data = await res.json();
      const container = document.getElementById('admin-audit-logs-table');
      if (!container) return;

      const logs = data.audit_logs || [];
      container.innerHTML = logs.map(l => {
        let actionBadge = 'bg-slate-100 text-slate-700';
        if (l.action.includes('VERIFY')) actionBadge = 'bg-emerald-100 text-emerald-800';
        if (l.action.includes('EDIT')) actionBadge = 'bg-blue-100 text-blue-800';
        if (l.action.includes('CONSENT')) actionBadge = 'bg-purple-100 text-purple-800';
        if (l.action.includes('LOGIN')) actionBadge = 'bg-amber-100 text-amber-800';
        if (l.action.includes('ACCOUNT')) actionBadge = 'bg-indigo-100 text-indigo-800';
        if (l.action.includes('RADIOLOGY')) actionBadge = 'bg-purple-100 text-purple-800';

        return `
          <tr class="hover:bg-slate-50 text-xs border-b border-slate-100">
            <td class="p-3 whitespace-nowrap font-mono text-slate-500">${l.timestamp.substring(0,19).replace('T', ' ')}</td>
            <td class="p-3">
              <span class="px-2 py-0.5 rounded text-[10px] font-bold ${actionBadge}">${l.action}</span>
            </td>
            <td class="p-3 font-medium text-slate-900">${l.user_id || 'System'} <span class="text-[10px] text-slate-500 font-normal">(${l.role || 'N/A'})</span></td>
            <td class="p-3 text-slate-600">${l.details || ''}</td>
            <td class="p-3 font-mono text-slate-400 text-[11px]">${l.ip_address || '127.0.0.1'}</td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    }
  },

  async loadStaffAccounts() {
    try {
      const res = await fetch('/api/auth/admin/staff-accounts');
      const data = await res.json();
      const container = document.getElementById('admin-staff-accounts-table');
      if (!container) return;

      const accounts = data.staff_accounts || [];
      container.innerHTML = accounts.map(a => {
        const isActive = a.account_status === 'ACTIVE';
        const roleBadgeClass = a.role === 'DOCTOR' ? 'bg-blue-100 text-blue-800' : (a.role === 'RADIOLOGIST' ? 'bg-purple-100 text-purple-800' : 'bg-emerald-100 text-emerald-800');

        return `
          <tr class="hover:bg-slate-50 text-xs border-b border-slate-100">
            <td class="p-3.5 font-mono font-bold text-slate-900">${a.login_id}</td>
            <td class="p-3.5">
              <div class="font-bold text-slate-900">${a.full_name}</div>
              <div class="text-[11px] text-slate-500">${a.email || 'No email registered'} • ${a.department || ''}</div>
            </td>
            <td class="p-3.5">
              <span class="px-2 py-0.5 rounded text-[10px] font-bold ${roleBadgeClass}">${a.role}</span>
            </td>
            <td class="p-3.5">
              ${isActive
                ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">Active</span>`
                : `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-100 text-red-800">Inactive</span>`
              }
              ${a.must_change_password ? '<span class="ml-1 text-[10px] text-amber-600 font-bold">(Must change password)</span>' : ''}
            </td>
            <td class="p-3.5 font-mono text-[11px] text-slate-500">${a.created_at ? a.created_at.substring(0,10) : 'N/A'}</td>
            <td class="p-3.5 text-right">
              ${isActive ? `
                <button onclick="AdminPortal.confirmDeactivate('${a.staff_id}', '${a.login_id}')" 
                        class="px-3 py-1 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 text-xs font-semibold transition">
                  Deactivate
                </button>
              ` : `
                <button onclick="AdminPortal.toggleStatus('${a.staff_id}', 'ACTIVE')" 
                        class="px-3 py-1 rounded-lg border border-emerald-200 text-emerald-600 hover:bg-emerald-50 text-xs font-semibold transition">
                  Activate
                </button>
              `}
            </td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      console.error('Failed to load staff accounts:', err);
    }
  },

  openGenerateCredentialsModal(defaultRole = 'DOCTOR') {
    const modal = document.getElementById('generate-credentials-modal');
    const roleSelect = document.getElementById('gen-staff-role');
    const resultBox = document.getElementById('gen-credentials-result');
    const formBox = document.getElementById('gen-credentials-form');

    if (roleSelect) roleSelect.value = defaultRole;
    if (resultBox) resultBox.classList.add('hidden');
    if (formBox) formBox.classList.remove('hidden');
    if (modal) modal.classList.remove('hidden');
  },

  closeGenerateCredentialsModal() {
    const modal = document.getElementById('generate-credentials-modal');
    if (modal) modal.classList.add('hidden');
  },

  async handleGenerateCredentials(e) {
    if (e) e.preventDefault();
    const role = document.getElementById('gen-staff-role')?.value || 'DOCTOR';
    const fullName = document.getElementById('gen-staff-name')?.value.trim();
    const email = document.getElementById('gen-staff-email')?.value.trim();
    const dept = document.getElementById('gen-staff-dept')?.value.trim();
    const spec = document.getElementById('gen-staff-spec')?.value.trim();

    if (!fullName) {
      App.showToast('Please enter the staff member full name.', 'warning');
      return;
    }

    try {
      const res = await fetch('/api/auth/admin/generate-credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role: role,
          full_name: fullName,
          email: email,
          department: dept,
          specialization: spec
        })
      });
      const data = await res.json();
      if (!res.ok) {
        App.showToast(data.detail || 'Failed to generate credentials', 'warning');
        return;
      }

      this.lastGeneratedCredentials = data.credentials;
      this.displayGeneratedCredentials(data.credentials);
      await this.loadStaffAccounts();
      await this.loadAuditLogs();
      App.showToast(`Credentials generated for ${data.credentials.login_id}!`);
    } catch (err) {
      App.showToast('Network error during credential generation.', 'warning');
    }
  },

  displayGeneratedCredentials(creds) {
    const formBox = document.getElementById('gen-credentials-form');
    const resultBox = document.getElementById('gen-credentials-result');
    const loginIdEl = document.getElementById('gen-result-login-id');
    const tempPwdEl = document.getElementById('gen-result-temp-pwd');
    const roleEl = document.getElementById('gen-result-role');
    const nameEl = document.getElementById('gen-result-name');

    if (loginIdEl) loginIdEl.innerText = creds.login_id;
    if (tempPwdEl) tempPwdEl.innerText = creds.temporary_password;
    if (roleEl) roleEl.innerText = creds.role;
    if (nameEl) nameEl.innerText = creds.full_name;

    if (formBox) formBox.classList.add('hidden');
    if (resultBox) resultBox.classList.remove('hidden');
    if (window.lucide) window.lucide.createIcons();
  },

  copyCredentials() {
    if (!this.lastGeneratedCredentials) return;
    const text = `ArogyaMitra Staff Credentials\nRole: ${this.lastGeneratedCredentials.role}\nName: ${this.lastGeneratedCredentials.full_name}\nLogin ID: ${this.lastGeneratedCredentials.login_id}\nTemporary Password: ${this.lastGeneratedCredentials.temporary_password}\n(First login will require setting a new password)`;
    navigator.clipboard.writeText(text).then(() => {
      App.showToast('Credentials copied to clipboard!', 'success');
    });
  },

  confirmDeactivate(staffId, loginId) {
    if (confirm(`Are you sure you want to deactivate staff account "${loginId}"? The user will be unable to log in, but historical audit trails and records remain preserved.`)) {
      this.toggleStatus(staffId, 'INACTIVE');
    }
  },

  async toggleStatus(staffId, newStatus) {
    try {
      const res = await fetch('/api/auth/admin/toggle-account-status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          staff_id: staffId,
          account_status: newStatus
        })
      });
      const data = await res.json();
      if (!res.ok) {
        App.showToast(data.detail || 'Status update failed', 'warning');
        return;
      }

      App.showToast(data.message, 'success');
      await this.loadStaffAccounts();
      await this.loadAuditLogs();
    } catch (err) {
      App.showToast('Failed to update account status.', 'warning');
    }
  }
};

window.AdminPortal = AdminPortal;
