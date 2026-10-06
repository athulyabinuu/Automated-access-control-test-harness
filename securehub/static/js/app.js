/* SECUREHUB Enterprise Security Portal - Main JavaScript */

document.addEventListener('DOMContentLoaded', () => {
    // -------------------------------------------------------------
    // LOGOUT IMPLEMENTATION (STRICT COMPLIANCE WITH REQ #8)
    // -------------------------------------------------------------
    const logoutBtn = document.getElementById('logout-button');
    let isLoggingOut = false;

    if (logoutBtn) {
        logoutBtn.addEventListener('click', async (e) => {
            e.preventDefault();

            // Prevent duplicate logout calls
            if (isLoggingOut) return;
            isLoggingOut = true;

            // Update UI state
            logoutBtn.disabled = true;
            const textSpan = logoutBtn.querySelector('span:not(.logout-icon)');
            if (textSpan) {
                textSpan.textContent = 'Signing out...';
            }

            try {
                const response = await fetch('/api/auth/logout', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        // Redirect browser to login page
                        window.location.href = '/login';
                        return;
                    }
                }
                
                // Fallback redirect if status was OK
                window.location.href = '/login';

            } catch (err) {
                console.error('Logout error:', err);
                // Even on error, redirect to login for safety
                window.location.href = '/login';
            }
        });
    }

    // -------------------------------------------------------------
    // AUTO-DISMISS ALERT MESSAGES
    // -------------------------------------------------------------
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.5s ease';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });
});
