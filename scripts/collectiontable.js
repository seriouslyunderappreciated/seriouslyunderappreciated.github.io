$(document).ready(function() {

    $.tablesorter.addParser({
        id: 'deviceParser',
        is: function() {
            return false;
        },
        format: function(s, table, cell) {
            return $(cell).attr('data-value') || '';
        },
        type: 'text'
    });

    $.get('data/collection.csv', function(data) {
        var lines = data.split('\n');
        if (!lines || lines.length === 0) return;
        var headers = lines[0].split(',');

        for (var i = 1; i < lines.length; i++) {
            if (!lines[i].trim()) continue;
            var row = lines[i].split(',');
            if (row.length === headers.length) {
                var tableRow = '<tr>';
                for (var j = 0; j < headers.length; j++) {
                    var cell = row[j].trim();
                    var dataValue = cell.replace(/\[hd\]|\[retro\]|\[switch\]/g, '').trim();
                    var displayCell = cell
                        .replace(/\[hd\]/g, '<img alt="Remake" title="Remake" src="images/hd.png" class="icon">')
                        .replace(/\[retro\]/g, '<img alt="Emulated" title="Emulated" src="images/retro.png" class="icon">')
                        .replace(/\[switch\]/g, '<img alt="Switch" title="Switch" src="images/switch.png" class="icon">');

                    if (j === 1) {
                        tableRow += '<td class="cen hide-column" data-value="' + dataValue + '">' + displayCell + '</td>';
                    } else if (j === (headers.length - 1)) {
                        tableRow += '<td class="cen hide-column" data-value="' + (cell === 'Yes' ? 'Yes' : '') + '">' + (cell === 'Yes' ? 'Yes' : '') + '</td>';
                    } else if (j === 0 || j === 3) {
                        tableRow += '<td class="cen nowrap" data-value="' + dataValue + '">' + displayCell + '</td>';
                    } else {
                        tableRow += '<td class="cen" data-value="' + dataValue + '">' + displayCell + '</td>';
                    }
                }
                tableRow += '</tr>';
                $('#myTable tbody').append(tableRow);
            }
        }

        var headerCount = $('#myTable thead th').length;
        var headersConfig = {};
        for (var c = 0; c < headerCount; c++) {
            headersConfig[c] = {
                lockedOrder: 'asc'
            };
        }
        $('#myTable thead th').each(function(index) {
            if (!$(this).hasClass('sortable')) {
                headersConfig[index].sorter = false;
            }
        });
        headersConfig[3].sorter = 'deviceParser';

        $('#myTable').tablesorter({
            sortList: [
                [0, 0],
                [1, 0],
                [2, 0],
                [3, 0]
            ],
            headers: headersConfig,
            widgets: ["filter"],
            widgetOptions: {
                filter_defaultAttrib: 'data-value',
                filter_columnFilters: true,
                filter_columnAnyMatch: true
            }
        });
    }).fail(function() {
        console.error('Failed to load collection.csv');
    });
});
