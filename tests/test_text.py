from fastkwan.text import reorder_syndrome_text


def test_the_syndrome_type_goes_before_its_symptoms():
    text = "症狀: 咳嗽 發熱 證型: 風寒證 病機: x"
    assert reorder_syndrome_text(text) == "證型: 風寒證\n症狀: 咳嗽 發熱\n\n病機: x"


def test_every_entry_is_reordered():
    text = "症狀: a 證型: 甲證 症狀: b 證型: 乙證 end"
    assert reorder_syndrome_text(text) == "證型: 甲證\n症狀: a\n\n證型: 乙證\n症狀: b\n\nend"


def test_text_without_the_markers_is_unchanged():
    assert reorder_syndrome_text("nothing to reorder") == "nothing to reorder"
    assert reorder_syndrome_text("") == ""
