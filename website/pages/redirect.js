
(function() {
    var path = window.location.pathname;

    const TARGETS = [ 'issue', 'issues' ]
    for (const target of TARGETS) {
        if (path == target) {
                window.location.href = 'https://github.com/Breakthrough/PySceneDetect/issues/';
        }
    }

    const PREFIXES = ['/issue/', '/issues/']
    for (const prefix of PREFIXES) {
        if (path.startsWith(prefix)) {
            var issueNumber = path.substring(prefix.length);
            if (issueNumber) {
                var newUrl = 'https://github.com/Breakthrough/PySceneDetect/issues/' + issueNumber;
                window.location.href = newUrl;
            }
        }
    }
})();
