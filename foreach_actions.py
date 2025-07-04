import sys
import renderdoc
rd = renderdoc


def iterAction(d, controller, indent=''):
    print('%s%d-%d: %s' % (indent, d.eventId,d.actionId, d.GetName(controller.GetStructuredFile())))
    # 判断是否是绘制调用
    if d.flags & rd.ActionFlags.Drawcall:
        if d.flags & rd.ActionFlags.Indexed:
            print('%s    Index drawing: Index=%d trs=%d' % (indent, d.numIndices, d.numIndices/3))
    # 递归子 action
    for c in d.children:
        iterAction(c, controller, indent + '    ')
        

def foreachActions(controller):
	# Iterate over all of the root actions
	for d in controller.GetRootActions():
		iterAction(d,controller)

	# Start iterating from the first real action as a child of markers
	action = controller.GetRootActions()[0]

	while len(action.children) > 0:
		action = action.children[0]

	# Counter for which pass we're in
	passnum = 0
	# Counter for how many actions are in the pass
	passcontents = 0
	# Whether we've started seeing actions in the pass - i.e. we're past any
	# starting clear calls that may be batched together
	inpass = False

	print("Pass #0 starts with %d: %s" % (action.eventId, action.GetName(controller.GetStructuredFile())))

	while action != None:
		# When we encounter a clear
		if action.flags & rd.ActionFlags.Clear:
			if inpass:
				print("Pass #%d contained %d actions" % (passnum, passcontents))
				passnum += 1
				print("Pass #%d starts with %d: %s" % (passnum, action.eventId, action.GetName(controller.GetStructuredFile())))
				passcontents = 0
				inpass = False
		else:
			passcontents += 1
			inpass = True

		# Advance to the next action
		action = action.next
		if action is None:
			break

	if inpass:
		print("Pass #%d contained %d actions" % (passnum, passcontents))

