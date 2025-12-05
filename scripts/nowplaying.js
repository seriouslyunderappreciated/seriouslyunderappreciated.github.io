$(document).ready(function() {
    function hideSectionIfEmpty(sectionSelector, content) {
        if (!content || (Array.isArray(content) && content.length === 0) || (typeof content === 'object' && Object.keys(content).length === 0)) {
            $(sectionSelector).hide();
            return true;
        }
        return false;
    }
    $.get('data/atm.txt', function(data) {
        var lines = data.trim().split('\n').map(l => l.trim()).filter(l => l !== '');
        if (hideSectionIfEmpty('#nowPlayingSection', lines)) return;
        let html = lines.map(line => `
            <div class="nowPlayingCard">
                ${line}
            </div>
        `).join('');
        $('#nowPlayingList').html(html);
    }).fail(function() {
        hideSectionIfEmpty('#nowPlayingSection', {});
    });
});
