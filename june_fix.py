import json
import os
import os.path

#this script fixes:
# 1. pinner_id incorrectly being called pinner in quote objects
# 2. attachments being incorrectly included in message contents
# 3. pinner_id incorrectly being a tuple of one

def fix_obj(o):
	if "pinner" in o:
		o["pinner_id"] = o["pinner"]
		del o["pinner"]
	if "content" in o and "\nATTACHMENT:" in o["content"]:
		#print("Content is " + o['content'])
		#print()
		o['content'] = o['content'].split("\nATTACHMENT", 1)[0]
		#print()
	if "pinner_id" in o and isinstance(o['pinner_id'], (list, tuple)):
		o['pinner_id'] = o['pinner_id'][0]
	if "messages" in o:
		o['messages'] = [fix_obj(m) for m in o['messages']]
	return o

for d in os.walk('pins'):
	for fn in d[2]:
		if fn.endswith(".json"):
			p = os.path.join(d[0], fn)
			print("running on " + p)
			with open(p) as f:
				j = json.load(f)

			# j is my top-level array
			# nj is my new top-level array
			#nj = [fix_obj(o) for o in j]
			nj = []
			for o in j:
				nj.append(fix_obj(o))

			with open(p, 'w') as g:
				json.dump(nj, g)