"""The symptom-extraction prompt. It used to be pasted twice, in /syndrome and in /prescription."""

NER_PROMPT = """為症狀進行NER, 请只按例子output NER的内容，不需要症状NER以外任何东西

            例子：
            input
            - 患者最近情况好一点了，已经转阴。
            - 患者在日本时自己发烧，回香港后看中医。
            - 中医给患者开的中药可以舒缓症状，有抗病毒功效。
            - 患者有些痰，喉咙有点干，胃口正常，睡眠质量好。
            - 患者咳嗽两天，有些感冒，鼻塞、鼻水倒流，喉嚨有些痛和乾，有痰黏著喉嚨，大便正常，睡眠六至七个小时，舌头有点红，吃过炸鸡。
            - 中医师会给患者开药治疗感冒
output：
            痰，喉嚨干，感冒，鼻塞，咳嗽"""
