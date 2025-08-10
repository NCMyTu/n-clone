# TODO: 
# when user clicks go back button from route /g/doujinshi_id/page_num,
# bring them back to /g/doujinshi_id instead of /g/doujinshi_id/page_num-1
# TODO:
# bring the doujin format inside render_doujinshi_preview to DOujinshi class
import os
from flask import Flask, render_template, send_from_directory
import pathlib
import sqlite3
import db.db_util as dbu

app = Flask(__name__)
app.url_map.strict_slashes = False

DB_PATH = "db/collection.db.sqlite"
ROOT_PREFIX = "C:/Users/ncmt/Desktop/Classified/"

@app.route("/")
def render_home():
	return render_template(
		"home.html"
	)

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.route("/g/<int:doujinshi_id>")
def render_doujinshi_preview(doujinshi_id):
	doujinshi = dbu.get_doujinshi(DB_PATH, doujinshi_id)

	doujinshi["before"] = ""
	doujinshi["pretty"] = ""
	doujinshi["ater"] = ""
	doujinshi["before_original"] = ""
	doujinshi["pretty_original"] = ""
	doujinshi["ater_original"] = ""

	if not doujinshi["bold_name"]:
		doujinshi["pretty"] = doujinshi["full_name"]
	else:
		start_index = doujinshi["full_name"].find(doujinshi["bold_name"])
		print(start_index)
		if start_index != -1:
			doujinshi["before"] = doujinshi["full_name"][:start_index]
			doujinshi["pretty"] = doujinshi["bold_name"]
			doujinshi["after"] = doujinshi["full_name"][start_index + len(doujinshi["bold_name"]):]
		else:
			doujinshi["pretty"] = doujinshi["full_name"]

	if doujinshi["full_name_original"]:
		if not doujinshi["bold_name_original"]:
			doujinshi["pretty_original"] = doujinshi["full_name_original"]
		else:
			start_index = doujinshi["full_name_original"].find(doujinshi["bold_name_original"])
			print(start_index)
			if start_index != -1:
				doujinshi["before_original"] = doujinshi["full_name_original"][:start_index]
				doujinshi["pretty_original"] = doujinshi["bold_name_original"]
				doujinshi["after_original"] = doujinshi["full_name_original"][start_index + len(doujinshi["bold_name_original"]):]
			else:
				doujinshi["pretty_original"] = doujinshi["full_name_original"]

	for k, v in doujinshi.items():
		print(k, v)

	return render_template(
		'doujinshi_preview.html', 
		doujinshi=doujinshi,
		doujinshi_id=doujinshi_id
	)

@app.route('/g/<int:doujinshi_id>/<int:page_order_number>')
def serve_image(doujinshi_id, page_order_number):
	doujinshi = dbu.get_doujinshi(DB_PATH, doujinshi_id)

	return send_from_directory(
		pathlib.Path(ROOT_PREFIX, doujinshi["path"]).as_posix(), 
		doujinshi["pages"][page_order_number-1]
	)

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=62222, debug=True)