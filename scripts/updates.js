$(document).ready(function() {
    function renderBuilds(data) {
        var section = document.getElementById('latestPatchesSection');
        var container = document.getElementById('latest-patches');

        if (hideSectionIfEmpty(section, data)) return;

        container.innerHTML = '';

        Object.values(data || {}).forEach(function(entry) {
            if (!entry || !entry.steamheader) return;

            var card = document.createElement('a');
            card.className = 'patch-entry';
            card.href = entry.steamdburl || '#';
            card.target = '_blank';
            card.rel = 'noopener noreferrer';

            var img = document.createElement('img');
            img.src = entry.steamheader || '';
            img.alt = entry.title || 'Steam Build';
            card.appendChild(img);

            if (entry.date) {
                var overlay = document.createElement('div');
                overlay.className = 'patch-date-overlay';
                overlay.textContent = entry.date;
                card.appendChild(overlay);
            }

            container.appendChild(card);
        });
    }

    function hideSectionIfEmpty(section, content) {
        if (!content || (Array.isArray(content) && content.length === 0) || (typeof content === 'object' && Object.keys(content).length === 0)) {
            $(section).hide();
            return true;
        }
        return false;
    }

    fetch('data/temp.json', {
            cache: "no-store"
        })
        .then(function(resp) {
            if (!resp.ok) throw new Error('Network response was not ok');
            return resp.json();
        })
        .then(renderBuilds)
        .catch(function(err) {
            hideSectionIfEmpty('#latestPatchesSection', {});
            console.error('Failed to load build info:', err);
        });
});
