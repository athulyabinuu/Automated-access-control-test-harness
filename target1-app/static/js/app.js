/**
 * SecureLab - Access Control Security Training Platform
 * Client-Side Application Logic & JWT Access Control Integration
 */

const SecureLab = (() => {
    const TOKEN_KEY = 'securelab_jwt_token';
    const USER_KEY = 'securelab_user_data';

    // ----------------------------------------------------
    // Authentication Helpers
    // ----------------------------------------------------

    function getToken() {
        return localStorage.getItem(TOKEN_KEY);
    }

    function setAuth(token, user) {
        localStorage.setItem(TOKEN_KEY, token);
        if (user) {
            localStorage.setItem(USER_KEY, JSON.stringify(user));
        }
    }

    function getAuthUser() {
        const data = localStorage.getItem(USER_KEY);
        try {
            return data ? JSON.parse(data) : null;
        } catch (e) {
            return null;
        }
    }

    function clearAuth() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
    }

    function logout() {
        clearAuth();
        window.location.href = '/login';
    }

    // ----------------------------------------------------
    // API Fetch Wrapper (Preserves strict backend JWT auth)
    // ----------------------------------------------------

    async function apiFetch(endpoint, options = {}) {
        const token = getToken();
        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            ...(options.headers || {})
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(endpoint, {
                ...options,
                headers
            });

            let data = null;
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                data = await response.json();
            } else {
                data = await response.text();
            }

            return {
                status: response.status,
                ok: response.ok,
                data
            };
        } catch (error) {
            console.error('API Fetch error:', error);
            return {
                status: 0,
                ok: false,
                data: { error: error.message }
            };
        }
    }

    // ----------------------------------------------------
    // Global User Bar Updater
    // ----------------------------------------------------

    async function updateTopbarUser() {
        const token = getToken();
        const pill = document.getElementById('user-pill');
        const loginLink = document.getElementById('topbar-login-link');
        const logoutBtn = document.getElementById('logout-btn');

        if (!token) {
            if (pill) pill.style.display = 'none';
            if (loginLink) loginLink.style.display = 'inline-flex';
            if (logoutBtn) logoutBtn.style.display = 'none';
            return null;
        }

        // Fetch latest /api/me
        const res = await apiFetch('/api/me');
        if (res.ok && res.data) {
            const user = res.data;
            setAuth(token, user);

            if (pill) pill.style.display = 'flex';
            if (loginLink) loginLink.style.display = 'none';
            if (logoutBtn) {
                logoutBtn.style.display = 'inline-flex';
                logoutBtn.onclick = logout;
            }

            const nameEl = document.getElementById('pill-username');
            const roleEl = document.getElementById('pill-role');
            const avatarEl = document.getElementById('pill-avatar');

            if (nameEl) nameEl.textContent = user.username;
            if (roleEl) roleEl.textContent = user.role;
            if (avatarEl) avatarEl.textContent = user.username.charAt(0).toUpperCase();

            // Admin sidebar link visibility hint (cosmetic only, backend enforces)
            const adminLinks = document.querySelectorAll('.admin-nav-item');
            adminLinks.forEach(link => {
                if (user.role === 'admin') {
                    link.style.display = 'flex';
                }
            });

            return user;
        } else {
            // Token expired or invalid
            clearAuth();
            if (window.location.pathname !== '/login' && window.location.pathname !== '/products') {
                window.location.href = '/login';
            }
            return null;
        }
    }

    // ----------------------------------------------------
    // Guard for Protected Pages
    // ----------------------------------------------------

    async function requireAuth() {
        const token = getToken();
        if (!token) {
            window.location.href = '/login';
            return null;
        }
        return await updateTopbarUser();
    }

    // ----------------------------------------------------
    // Page: Login (/login)
    // ----------------------------------------------------

    function initLoginPage() {
        const form = document.getElementById('login-form');
        const errorAlert = document.getElementById('login-error');
        const usernameInput = document.getElementById('username');
        const passwordInput = document.getElementById('password');
        const submitBtn = document.getElementById('login-submit-btn');

        // Check if already authenticated
        if (getToken()) {
            apiFetch('/api/me').then(res => {
                if (res.ok) {
                    window.location.href = '/dashboard';
                }
            });
        }

        // Demo credential quick-fill chips
        document.querySelectorAll('.demo-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const u = chip.getAttribute('data-user');
                const p = chip.getAttribute('data-pass');
                if (usernameInput) usernameInput.value = u;
                if (passwordInput) passwordInput.value = p;
                if (errorAlert) errorAlert.style.display = 'none';
            });
        });

        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                if (errorAlert) errorAlert.style.display = 'none';

                const username = usernameInput.value.trim();
                const password = passwordInput.value;

                if (!username || !password) {
                    if (errorAlert) {
                        errorAlert.textContent = 'Please enter both username and password.';
                        errorAlert.style.display = 'flex';
                    }
                    return;
                }

                submitBtn.disabled = true;
                submitBtn.textContent = 'Authenticating...';

                const res = await apiFetch('/api/login', {
                    method: 'POST',
                    body: JSON.stringify({ username, password })
                });

                submitBtn.disabled = false;
                submitBtn.textContent = 'Sign In to SecureLab';

                if (res.ok && res.data && res.data.token) {
                    setAuth(res.data.token);
                    // Fetch user details immediately
                    const meRes = await apiFetch('/api/me');
                    if (meRes.ok) {
                        setAuth(res.data.token, meRes.data);
                    }
                    window.location.href = '/dashboard';
                } else {
                    const errMsg = (res.data && res.data.error) ? res.data.error : 'Invalid username or password';
                    if (errorAlert) {
                        errorAlert.textContent = errMsg;
                        errorAlert.style.display = 'flex';
                    }
                }
            });
        }
    }

    // ----------------------------------------------------
    // Page: Dashboard (/dashboard)
    // ----------------------------------------------------

    async function initDashboardPage() {
        const user = await requireAuth();
        if (!user) return;

        // Welcome banner
        const welcomeUserEl = document.getElementById('dash-welcome-user');
        const roleBadgeEl = document.getElementById('dash-role-badge');
        if (welcomeUserEl) welcomeUserEl.textContent = user.username;
        if (roleBadgeEl) {
            roleBadgeEl.textContent = user.role.toUpperCase();
            roleBadgeEl.className = `badge ${user.role === 'admin' ? 'badge-admin' : 'badge-user'}`;
        }

        // Stats
        const userIdEl = document.getElementById('dash-user-id');
        const userRoleEl = document.getElementById('dash-role-name');
        const orderIdEl = document.getElementById('dash-assigned-order');

        if (userIdEl) userIdEl.textContent = user.user_id;
        if (userRoleEl) userRoleEl.textContent = user.role.toUpperCase();
        if (orderIdEl) {
            if (user.role === 'admin') {
                orderIdEl.textContent = 'All (101, 102)';
            } else if (user.user_id === 2) {
                orderIdEl.textContent = '101';
            } else if (user.user_id === 3) {
                orderIdEl.textContent = '102';
            } else {
                orderIdEl.textContent = 'N/A';
            }
        }

        // Token claims preview
        const tokenPreviewEl = document.getElementById('dash-token-claims');
        if (tokenPreviewEl) {
            tokenPreviewEl.textContent = JSON.stringify({
                user_id: user.user_id,
                username: user.username,
                role: user.role,
                auth_scheme: 'JWT HS256',
                access_control: user.role === 'admin' ? 'Administrative (any)' : 'Role-based (own)'
            }, null, 2);
        }

        // Load Products preview
        const prodPreviewList = document.getElementById('dash-products-preview');
        if (prodPreviewList) {
            const prodRes = await apiFetch('/api/products');
            if (prodRes.ok && prodRes.data && prodRes.data.products) {
                prodPreviewList.innerHTML = prodRes.data.products.map(p => `
                    <tr>
                        <td class="mono">#00${p.id}</td>
                        <td style="font-weight: 600; color: #f1f5f9;">${escapeHtml(p.name)}</td>
                        <td><span class="badge badge-cyan">In Stock</span></td>
                        <td><span class="badge badge-success">Public</span></td>
                    </tr>
                `).join('');
            }
        }
    }

    // ----------------------------------------------------
    // Page: Products (/products)
    // ----------------------------------------------------

    async function initProductsPage() {
        await updateTopbarUser();

        const grid = document.getElementById('products-grid');
        const countEl = document.getElementById('products-count');
        const evidenceEl = document.getElementById('products-api-evidence');

        const res = await apiFetch('/api/products');

        if (evidenceEl) {
            evidenceEl.textContent = JSON.stringify(res.data, null, 2);
        }

        if (res.ok && res.data && res.data.products) {
            const products = res.data.products;
            if (countEl) countEl.textContent = products.length;

            const iconMap = {
                1: '💻', // Laptop
                2: '⌨️', // Keyboard
                3: '🖱️'  // Mouse
            };

            const descMap = {
                1: 'High-performance workstation for security auditing and penetration testing.',
                2: 'Mechanical keyboard with tactile switches for rapid command execution.',
                3: 'Precision optical mouse engineered for multi-monitor operations.'
            };

            const priceMap = {
                1: '$1,299.00',
                2: '$149.00',
                3: '$79.00'
            };

            grid.innerHTML = products.map(p => `
                <div class="product-card">
                    <div class="product-image-container">
                        <span style="font-size: 3rem;">${iconMap[p.id] || '📦'}</span>
                    </div>
                    <div class="product-body">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
                            <h3 class="product-title">${escapeHtml(p.name)}</h3>
                            <span class="badge badge-cyan mono">ID: ${p.id}</span>
                        </div>
                        <p class="product-desc">${descMap[p.id] || 'Cybersecurity hardware and accessories.'}</p>
                        <div class="product-footer">
                            <span class="product-price">${priceMap[p.id] || '$99.00'}</span>
                            <span class="badge badge-success">Public API Access</span>
                        </div>
                    </div>
                </div>
            `).join('');
        } else {
            grid.innerHTML = `<div class="alert alert-danger">Failed to load product catalog from /api/products</div>`;
        }
    }

    // ----------------------------------------------------
    // Page: Profile (/profile)
    // ----------------------------------------------------

    async function initProfilePage() {
        const user = await requireAuth();
        if (!user) return;

        // Fetch own profile
        const profileRes = await apiFetch(`/api/users/${user.user_id}`);
        const usernameInput = document.getElementById('profile-username');
        const emailInput = document.getElementById('profile-email');
        const idDisplay = document.getElementById('profile-user-id');
        const roleDisplay = document.getElementById('profile-role');
        const statusAlert = document.getElementById('profile-status-alert');

        if (profileRes.ok && profileRes.data) {
            const prof = profileRes.data;
            if (usernameInput) usernameInput.value = prof.username;
            if (emailInput) emailInput.value = prof.email || `${prof.username}@example.com`;
            if (idDisplay) idDisplay.textContent = prof.id;
            if (roleDisplay) {
                roleDisplay.textContent = user.role.toUpperCase();
                roleDisplay.className = `badge ${user.role === 'admin' ? 'badge-admin' : 'badge-user'}`;
            }
        }

        // Handle profile PATCH form
        const form = document.getElementById('profile-edit-form');
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                if (statusAlert) statusAlert.style.display = 'none';

                const newUsername = usernameInput.value.trim();
                const newEmail = emailInput.value.trim();

                const patchRes = await apiFetch(`/api/users/${user.user_id}`, {
                    method: 'PATCH',
                    body: JSON.stringify({
                        username: newUsername,
                        email: newEmail
                    })
                });

                if (statusAlert) {
                    if (patchRes.ok) {
                        statusAlert.className = 'alert alert-success';
                        statusAlert.textContent = 'Profile updated successfully via PATCH /api/users/' + user.user_id;
                        statusAlert.style.display = 'flex';
                        updateTopbarUser();
                    } else {
                        statusAlert.className = 'alert alert-danger';
                        statusAlert.textContent = (patchRes.data && patchRes.data.error) ? patchRes.data.error : 'Failed to update profile.';
                        statusAlert.style.display = 'flex';
                    }
                }
            });
        }

        // Horizontal Access Control (IDOR) Test Tool
        const idorBtn = document.getElementById('test-idor-user-btn');
        const idorInput = document.getElementById('test-idor-user-id');
        const idorOutput = document.getElementById('idor-user-output');
        const idorStatusBadge = document.getElementById('idor-user-status-badge');

        if (idorBtn && idorInput) {
            idorBtn.addEventListener('click', async () => {
                const targetId = idorInput.value.trim();
                if (!targetId) return;

                idorBtn.disabled = true;
                idorBtn.textContent = 'Testing...';

                const testRes = await apiFetch(`/api/users/${targetId}`);

                idorBtn.disabled = false;
                idorBtn.textContent = 'Probe Target Profile';

                if (idorStatusBadge) {
                    idorStatusBadge.textContent = `HTTP ${testRes.status}`;
                    idorStatusBadge.className = `status-indicator-badge status-${testRes.status}`;
                }

                if (idorOutput) {
                    idorOutput.textContent = JSON.stringify({
                        endpoint: `GET /api/users/${targetId}`,
                        status_code: testRes.status,
                        caller_role: user.role,
                        caller_id: user.user_id,
                        response: testRes.data,
                        security_result: testRes.status === 200 ? 'ACCESS GRANTED (Authorized/Admin)' : 'ACCESS DENIED (Horizontal Protection Active)'
                    }, null, 2);
                }
            });
        }
    }

    // ----------------------------------------------------
    // Page: Orders (/orders)
    // ----------------------------------------------------

    async function initOrdersPage() {
        const user = await requireAuth();
        if (!user) return;

        const tableBody = document.getElementById('orders-table-body');
        const orderSummaryEl = document.getElementById('order-summary-text');

        // Orders belonging to roles
        // user1 (id 2) -> order 101
        // user2 (id 3) -> order 102
        // admin (id 1) -> has 'any' access to orders 101 & 102
        const targetOrderIds = user.role === 'admin' ? [101, 102] : (user.user_id === 2 ? [101] : [102]);

        const fetchedOrders = [];
        for (const oid of targetOrderIds) {
            const res = await apiFetch(`/api/orders/${oid}`);
            if (res.ok && res.data) {
                fetchedOrders.push(res.data);
            }
        }

        if (orderSummaryEl) {
            if (user.role === 'admin') {
                orderSummaryEl.textContent = `Administrator view: Showing all orders accessible across the system (${fetchedOrders.length} orders).`;
            } else {
                orderSummaryEl.textContent = `Showing only your authorized personal order(s). Cross-user orders are strictly restricted.`;
            }
        }

        if (tableBody) {
            if (fetchedOrders.length === 0) {
                tableBody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No orders found.</td></tr>`;
            } else {
                tableBody.innerHTML = fetchedOrders.map(ord => `
                    <tr>
                        <td class="mono" style="font-weight: 700; color: var(--color-cyan);">#ORD-${ord.id}</td>
                        <td class="mono">User #${ord.user_id}</td>
                        <td style="font-weight: 600; color: #f1f5f9;">${escapeHtml(ord.item)}</td>
                        <td><span class="badge badge-success">Verified</span></td>
                        <td>
                            <button class="btn btn-secondary btn-sm" onclick="alert('Order #ORD-${ord.id}: ${escapeHtml(ord.item)}')">
                                View Details
                            </button>
                        </td>
                    </tr>
                `).join('');
            }
        }

        // Horizontal Access Control (IDOR) Test Tool
        const testBtn = document.getElementById('test-idor-order-btn');
        const testInput = document.getElementById('test-idor-order-id');
        const testOutput = document.getElementById('idor-order-output');
        const testStatusBadge = document.getElementById('idor-order-status-badge');

        if (testBtn && testInput) {
            testBtn.addEventListener('click', async () => {
                const targetId = testInput.value.trim();
                if (!targetId) return;

                testBtn.disabled = true;
                testBtn.textContent = 'Probing Order...';

                const testRes = await apiFetch(`/api/orders/${targetId}`);

                testBtn.disabled = false;
                testBtn.textContent = 'Test Order Access';

                if (testStatusBadge) {
                    testStatusBadge.textContent = `HTTP ${testRes.status}`;
                    testStatusBadge.className = `status-indicator-badge status-${testRes.status}`;
                }

                if (testOutput) {
                    testOutput.textContent = JSON.stringify({
                        endpoint: `GET /api/orders/${targetId}`,
                        http_status: testRes.status,
                        caller_role: user.role,
                        caller_user_id: user.user_id,
                        response_body: testRes.data,
                        analysis: testRes.status === 200 ? 'Access Permitted (Authorized owner or Admin)' : 'Access Forbidden (Horizontal Privilege Escalation Blocked)'
                    }, null, 2);
                }
            });
        }
    }

    // ----------------------------------------------------
    // Page: Users (/users)
    // ----------------------------------------------------

    async function initUsersPage() {
        const user = await requireAuth();
        if (!user) return;

        const adminContainer = document.getElementById('users-admin-view');
        const deniedContainer = document.getElementById('users-denied-view');
        const tableBody = document.getElementById('users-table-body');
        const deniedEvidence = document.getElementById('users-denied-evidence');

        // Probe GET /api/admin/users
        const res = await apiFetch('/api/admin/users');

        if (res.ok && res.data && res.data.users) {
            // Admin authorized view
            if (adminContainer) adminContainer.style.display = 'block';
            if (deniedContainer) deniedContainer.style.display = 'none';

            const userList = res.data.users;
            if (tableBody) {
                tableBody.innerHTML = userList.map(u => `
                    <tr>
                        <td class="mono">#00${u.id}</td>
                        <td style="font-weight: 700; color: #f1f5f9;">${escapeHtml(u.username)}</td>
                        <td class="mono" style="color: var(--text-secondary);">${escapeHtml(u.email || u.username + '@example.com')}</td>
                        <td>
                            <span class="badge ${u.id === 1 ? 'badge-admin' : 'badge-user'}">
                                ${u.id === 1 ? 'ADMIN' : 'USER'}
                            </span>
                        </td>
                        <td><span class="badge badge-success">ACTIVE</span></td>
                        <td>
                            <a href="/profile" class="btn btn-secondary btn-sm">Inspect</a>
                        </td>
                    </tr>
                `).join('');
            }
        } else {
            // Non-admin: 403 Forbidden properly received from backend
            if (adminContainer) adminContainer.style.display = 'none';
            if (deniedContainer) deniedContainer.style.display = 'block';

            if (deniedEvidence) {
                deniedEvidence.textContent = JSON.stringify({
                    endpoint: 'GET /api/admin/users',
                    http_status: res.status,
                    caller_role: user.role,
                    caller_username: user.username,
                    response: res.data,
                    enforcement: 'Vertical Privilege Escalation Prevented (Backend returned 403 Forbidden)'
                }, null, 2);
            }
        }
    }

    // ----------------------------------------------------
    // Page: Admin Dashboard (/admin)
    // ----------------------------------------------------

    async function initAdminPage() {
        const user = await requireAuth();
        if (!user) return;

        const adminContent = document.getElementById('admin-content');
        const deniedContent = document.getElementById('admin-denied-view');

        // Fetch /api/admin/stats
        const statsRes = await apiFetch('/api/admin/stats');

        if (statsRes.ok && statsRes.data) {
            if (adminContent) adminContent.style.display = 'block';
            if (deniedContent) deniedContent.style.display = 'none';

            // Populate stats
            const stats = statsRes.data;
            const totalUsersEl = document.getElementById('admin-total-users');
            const totalOrdersEl = document.getElementById('admin-total-orders');
            const totalProductsEl = document.getElementById('admin-total-products');

            if (totalUsersEl) totalUsersEl.textContent = stats.total_users;
            if (totalOrdersEl) totalOrdersEl.textContent = stats.total_orders;
            if (totalProductsEl) totalProductsEl.textContent = stats.total_products;

            // Load users table
            const usersRes = await apiFetch('/api/admin/users');
            const tableBody = document.getElementById('admin-users-table');
            if (usersRes.ok && usersRes.data && usersRes.data.users) {
                tableBody.innerHTML = usersRes.data.users.map(u => `
                    <tr>
                        <td class="mono">#00${u.id}</td>
                        <td style="font-weight: 700; color: #f1f5f9;">${escapeHtml(u.username)}</td>
                        <td class="mono">${escapeHtml(u.email || u.username + '@example.com')}</td>
                        <td><span class="badge ${u.id === 1 ? 'badge-admin' : 'badge-user'}">${u.id === 1 ? 'ADMIN' : 'USER'}</span></td>
                        <td>
                            <button class="btn btn-danger btn-sm" onclick="SecureLab.handleDeleteUser(${u.id})">
                                Delete
                            </button>
                        </td>
                    </tr>
                `).join('');
            }
        } else {
            // Vertical privilege protection active
            if (adminContent) adminContent.style.display = 'none';
            if (deniedContent) deniedContent.style.display = 'block';

            const evidenceEl = document.getElementById('admin-denied-evidence');
            if (evidenceEl) {
                evidenceEl.textContent = JSON.stringify({
                    endpoint: 'GET /api/admin/stats',
                    status: statsRes.status,
                    caller_role: user.role,
                    caller_username: user.username,
                    response: statsRes.data,
                    enforcement: 'Vertical Privilege Escalation Blocked by @token_required & Role Check'
                }, null, 2);
            }
        }
    }

    async function handleDeleteUser(userId) {
        if (!confirm(`Are you sure you want to test deleting user #${userId}?`)) return;

        const res = await apiFetch(`/api/admin/users/${userId}`, {
            method: 'DELETE'
        });

        const alertBox = document.getElementById('admin-action-alert');
        if (alertBox) {
            alertBox.style.display = 'flex';
            if (res.ok) {
                alertBox.className = 'alert alert-success';
                alertBox.textContent = `User #${userId} deleted successfully (${res.data.message || 'HTTP 200'}).`;
            } else {
                alertBox.className = 'alert alert-danger';
                alertBox.textContent = `Deletion rejected: ${res.data.error || 'Access denied'}`;
            }
        }
    }

    // Helper: HTML escape
    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    return {
        getToken,
        setAuth,
        getAuthUser,
        clearAuth,
        logout,
        apiFetch,
        updateTopbarUser,
        requireAuth,
        initLoginPage,
        initDashboardPage,
        initProductsPage,
        initProfilePage,
        initOrdersPage,
        initUsersPage,
        initAdminPage,
        handleDeleteUser
    };
})();
