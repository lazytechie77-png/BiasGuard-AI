from core_engine import scan_for_bias

# 1. Quote protection + apostrophe
t1 = "The incompetent mayor's plan was slammed. The senator said, \"This is draconian.\""
f, q = scan_for_bias(t1)
print([x["Phrase"] for x in f])   # expect ['incompetent', 'slammed']
print(q)                          # expect the draconian quote only

# 2. Hindi
t2 = 'सरकार की विनाशकारी नीति। मंत्री ने कहा, "यह तानाशाही है।"'
f, q = scan_for_bias(t2, "hindi")
print([x["Phrase"] for x in f])   # expect ['विनाशकारी']

# 3. Neutral text
f, q = scan_for_bias("The council approved the budget on Tuesday.")
print(f)                          # expect []