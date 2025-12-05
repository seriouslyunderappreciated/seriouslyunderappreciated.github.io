$(document).ready(function() {
    function renderBuilds(data) {
        var section = document.getElementById('latestPatchesSection');
        var container = document.getElementById('latest-patches');

        if (hideSectionIfEmpty(section, data)) return;

        container.innerHTML = '';

        Object.values(data || {}).forEach(function(entry) {
            if (!entry || !entry.steamheader) return;

            var card = document.createElement('div');
            card.className = 'patch-entry';

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

            var leftLink = document.createElement('a');
            leftLink.className = 'hover-zone left-zone';
            leftLink.href = entry.steamdburl || '#';
            leftLink.target = '_blank';
            leftLink.rel = 'noopener noreferrer';
            card.appendChild(leftLink);

            var rightLink = document.createElement('a');
            rightLink.className = 'hover-zone right-zone';
            rightLink.href = entry.rinurl || '#';
            rightLink.target = '_blank';
            rightLink.rel = 'noopener noreferrer';
            card.appendChild(rightLink);

            var leftText = document.createElement('div');
            leftText.className = 'hover-text left';
            leftText.textContent = 'Patch Notes';
            card.appendChild(leftText);

            var rightText = document.createElement('div');
            rightText.className = 'hover-text right';
            rightText.textContent = 'Download';
            card.appendChild(rightText);

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
