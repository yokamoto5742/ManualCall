"""audio_converterの単体テスト（μ-law⇔PCM16変換・ratecv state管理）"""

import audioop

from app.services.audio_converter import AudioConverter


def _sine_pcm16(num_samples: int, rate: int) -> bytes:
    """簡易のこぎり波PCM16を生成（依存を増やさず再現可能な信号を作る）"""
    samples = []
    for i in range(num_samples):
        value = (i % rate) * 4 - 2000
        value = max(-32768, min(32767, value))
        samples.append(value.to_bytes(2, "little", signed=True))
    return b"".join(samples)


def test_twilio_to_gemini_changes_rate_and_width():
    conv = AudioConverter()
    # μ-law 8kHz 160サンプル（20ms相当）
    mulaw = audioop.lin2ulaw(_sine_pcm16(160, 8000), 2)

    pcm_16k = conv.twilio_to_gemini(mulaw)

    # 8k→16kで概ね2倍のサンプル数、PCM16なのでバイト長は偶数
    assert len(pcm_16k) % 2 == 0
    assert len(pcm_16k) > len(mulaw) * 2


def test_gemini_to_twilio_changes_rate_and_width():
    conv = AudioConverter()
    pcm_16k = _sine_pcm16(320, 16000)

    mulaw_8k = conv.gemini_to_twilio(pcm_16k)

    # 16k→8kでμ-law（1バイト/サンプル）に縮む
    assert 0 < len(mulaw_8k) < len(pcm_16k)


def test_chunked_equals_oneshot_upstream():
    """ratecv stateがチャンクをまたいで保持されることの決定的検証（§2.2）

    一括変換とチャンク分割変換の結合結果が一致すれば、state管理は正しい。
    """
    pcm = _sine_pcm16(800, 8000)
    mulaw = audioop.lin2ulaw(pcm, 2)

    oneshot = AudioConverter().twilio_to_gemini(mulaw)

    conv = AudioConverter()
    chunk_size = 32  # μ-lawバイト（=サンプル数）境界で分割
    chunked = b"".join(
        conv.twilio_to_gemini(mulaw[i : i + chunk_size])
        for i in range(0, len(mulaw), chunk_size)
    )

    assert chunked == oneshot


def test_chunked_equals_oneshot_downstream():
    """下り方向でもstateがチャンクをまたいで保持される"""
    pcm = _sine_pcm16(1600, 16000)

    oneshot = AudioConverter().gemini_to_twilio(pcm)

    conv = AudioConverter()
    chunk_size = 64  # PCM16バイト（偶数で分割）
    chunked = b"".join(
        conv.gemini_to_twilio(pcm[i : i + chunk_size])
        for i in range(0, len(pcm), chunk_size)
    )

    assert chunked == oneshot


def test_separate_instances_have_independent_state():
    """接続ごとにstateが独立していること"""
    pcm = _sine_pcm16(800, 8000)
    mulaw = audioop.lin2ulaw(pcm, 2)

    conv_a = AudioConverter()
    conv_b = AudioConverter()
    # 同じ入力なら別インスタンスでも同一の出力になる（state混線がない）
    assert conv_a.twilio_to_gemini(mulaw) == conv_b.twilio_to_gemini(mulaw)
