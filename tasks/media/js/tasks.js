function linkify_plain(text) {
	if( !text ) return text;
	
	text = text.replace(/((https?\:\/\/|ftp\:\/\/)|(www\.))(\S+)(\w{2,4})(:[0-9]+)?(\/|\/([\w#!:.?+=&%@!\-\/]))?/gi,function(url){
		return '<a target="_blank" rel="nofollow" href="'+ url +'">'+ url +'</a>';
	});
	
	return text;
}

function load_user_profile(username) {
	var ul = $('#profile-tweets');
	$.jTwitter(username, 10, function(tweets){
		$.each(tweets, function(){
			date = new Date(this.created_at);
			date_fmt = date;
			ul.append('<li><span class="text">' + linkify_plain(this.text) + '</span><br /><span class="source">' + date_fmt + ' from ' + this.source + '</span></li>');
		});
	});
}
