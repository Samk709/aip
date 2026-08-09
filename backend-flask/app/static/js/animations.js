document.addEventListener('DOMContentLoaded', () => {
    // SPA Navigation Control
    const navItems = document.querySelectorAll('.nav-item');
    const viewSections = document.querySelectorAll('.view-section');

    // Make initial active view fully visible right away
    // Make initial active view trigger CSS animation
    const initView = document.querySelector('.view-section.active');
    if (initView) {
        initView.style.display = 'block';
    }

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = item.getAttribute('data-target');

            // Find current active view
            const currentView = document.querySelector('.view-section.active');

            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');

            if (currentView) {
                currentView.classList.remove('active');

                setTimeout(() => {
                    currentView.style.display = 'none';

                    // Fade in new view safely
                    const activeView = document.querySelector(targetId);
                    if (activeView) {
                        activeView.style.display = 'block';
                        // Small reflow to trigger CSS transition
                        void activeView.offsetWidth;
                        activeView.classList.add('active');
                    }
                }, 400); // Wait for fade out keyframe to finish
            } else {
                const activeView = document.querySelector(targetId);
                if (activeView) {
                    activeView.style.display = 'block';
                    void activeView.offsetWidth;
                    activeView.classList.add('active');
                }
            }
        });
    });
});
