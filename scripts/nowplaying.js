$(document).ready(function() {

    function hideSectionIfEmpty(sectionSelector, content) {
        if (!content || (Array.isArray(content) && content.length === 0) || (typeof content === 'object' && Object.keys(content).length === 0)) {
            $(sectionSelector).hide();
            return true;
        }
        return false;
    }

    $.get('data/atm.txt', function(data) {
        var lines = data.trim().split('\n').filter(line => line.trim() !== '');
        if (hideSectionIfEmpty('#nowPlayingSection', lines)) return;

        $('#nowPlayingList').empty();

        lines.forEach(function(line) {
            var gameDiv = $('<div class="nowPlayingItem"></div>').text(line);
            $('#nowPlayingList').append(gameDiv);
        });
    }).fail(function() {
        hideSectionIfEmpty('#nowPlayingSection', {});
    });
});
