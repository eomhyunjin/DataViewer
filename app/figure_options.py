"""matplotlib 내장 "Figure options"(Customize) 다이얼로그를 이 앱에 맞게 손질한 버전.

원본은 matplotlib.backends.qt_editor.figureoptions.figure_edit이다. matplotlib은
이 다이얼로그에서 필드 하나만 빼는 식의 공개 API를 제공하지 않아서, 함수 전체를
그대로 옮겨온 뒤 다음 두 가지를 뺐다:
(1) X/Y축 Scale(linear/log/symlog/logit) 드롭다운 — 이 앱이 다루는 장비 로그
    시계열 데이터에는 로그/symlog 축이 쓸모없고, 실수로 건드리면 그래프가 비어
    보이는 등 혼란만 준다는 사용자 피드백에 따른 것.
(2) Title/축 Min·Max·Label/legend 재생성 체크박스를 담은 "Axes" 탭 전체 — 축 편집은
    그래프에서 해당 축을 더블클릭하면 뜨는 `axis_edit()`으로 옮겨갔다(자세한 이유는
    `figure_edit()` docstring 참고). 그래서 이 파일에 남은 건 "Curves" 탭뿐이다.
matplotlib을 업그레이드할 때는 이 파일을 원본과 다시 비교해서 다른 변경 사항이
반영됐는지 확인해야 한다.
"""
from __future__ import annotations

from matplotlib import cbook, cm, colors as mcolors, markers, image as mimage
from matplotlib.backends.qt_compat import QtGui
from matplotlib.backends.qt_editor import _formlayout
from matplotlib.dates import DateConverter, num2date

LINESTYLES = {'-': 'Solid',
              '--': 'Dashed',
              '-.': 'DashDot',
              ':': 'Dotted',
              'None': 'None',
              }

DRAWSTYLES = {
    'default': 'Default',
    'steps-pre': 'Steps (Pre)', 'steps': 'Steps (Pre)',
    'steps-mid': 'Steps (Mid)',
    'steps-post': 'Steps (Post)'}

MARKERS = markers.MarkerStyle.markers


def figure_edit(axes, parent=None, on_apply=None):
    """Figure options를 연다. 라인(Curves) 스타일만 편집한다 — Axes 탭은 없다.

    matplotlib 원본은 Title/축 Min·Max·Label/legend 재생성 체크박스를 담은 "Axes" 탭을
    포함하지만, 이 앱에서는 뺐다: 축 Min/Max/Label 편집은 그래프에서 해당 축을 더블클릭하면
    뜨는 `axis_edit()`으로 옮겨갔는데(`axis_edit`이 멀티 Y축 각각을 지원하는 것과 달리 이
    Axes 탭은 항상 첫 번째 축(`axes` 인자)만 편집할 수 있어서 twinx로 만든 추가 Y축은 아예
    건드릴 수 없었다), 남은 Title/legend 체크박스는 이 앱에서 쓰이지 않는다.

    on_apply: OK/Apply를 눌러 변경사항이 반영된 직후 호출되는 콜백(인자 없음). 이 앱에서는
    범례 갱신(`PlotCanvas.refresh_legend`)을 넘겨받아, 커브 색을 바꾼 뒤 범례 아이콘도 최신
    색으로 다시 그리는 데 쓴다.
    """
    sep = (None, None)  # separator

    # Get / Curves
    #
    # 커브 목록은 axes 인자(호스트 축) 하나가 아니라 figure의 모든 축(twinx()로 만든
    # 멀티 Y축 포함)에서 모은다. 이 앱은 Y축으로 체크한 컬럼마다 별도의 twinx() 축에
    # 선을 하나씩 그리므로, axes.get_lines()만 쓰면 호스트 축(첫 번째 Y 컬럼)의 선
    # 하나만 돌려줘서 Curves 탭 드롭다운에 항목이 하나만 보이는 문제가 있었다.
    # figure.get_axes()는 축이 추가된 순서(호스트 -> 첫 twinx -> 다음 twinx...)를
    # 그대로 유지하므로, apply_callback에서 curves/labeled_lines를 같은 순서로
    # 인덱스 매칭하는 기존 로직은 그대로 둬도 된다.
    labeled_lines = []
    for ax in axes.get_figure().get_axes():
        for line in ax.get_lines():
            label = line.get_label()
            if label == '_nolegend_':
                continue
            labeled_lines.append((label, line))
    curves = []

    def prepare_data(d, init):
        """
        Prepare entry for FormLayout.

        *d* is a mapping of shorthands to style names (a single style may
        have multiple shorthands, in particular the shorthands `None`,
        `"None"`, `"none"` and `""` are synonyms); *init* is one shorthand
        of the initial style.

        This function returns a list suitable for initializing a
        FormLayout combobox, namely `[initial_name, (shorthand,
        style_name), (shorthand, style_name), ...]`.
        """
        if init not in d:
            d = {**d, init: str(init)}
        # Drop duplicate shorthands from dict (by overwriting them during
        # the dict comprehension).
        name2short = {name: short for short, name in d.items()}
        # Convert back to {shorthand: name}.
        short2name = {short: name for name, short in name2short.items()}
        # Find the kept shorthand for the style specified by init.
        canonical_init = name2short[d[init]]
        # Sort by representation and prepend the initial value.
        return ([canonical_init] +
                sorted(short2name.items(),
                       key=lambda short_and_name: short_and_name[1]))

    for label, line in labeled_lines:
        color = mcolors.to_hex(
            mcolors.to_rgba(line.get_color(), line.get_alpha()),
            keep_alpha=True)
        ec = mcolors.to_hex(
            mcolors.to_rgba(line.get_markeredgecolor(), line.get_alpha()),
            keep_alpha=True)
        fc = mcolors.to_hex(
            mcolors.to_rgba(line.get_markerfacecolor(), line.get_alpha()),
            keep_alpha=True)
        curvedata = [
            ('Label', label),
            sep,
            (None, '<b>Line</b>'),
            ('Line style', prepare_data(LINESTYLES, line.get_linestyle())),
            ('Draw style', prepare_data(DRAWSTYLES, line.get_drawstyle())),
            ('Width', line.get_linewidth()),
            ('Color (RGBA)', color),
            sep,
            (None, '<b>Marker</b>'),
            ('Style', prepare_data(MARKERS, line.get_marker())),
            ('Size', line.get_markersize()),
            ('Face color (RGBA)', fc),
            ('Edge color (RGBA)', ec)]
        curves.append([curvedata, label, ""])
    # Is there a curve displayed?
    has_curve = bool(curves)

    # Get ScalarMappables.
    labeled_mappables = []
    for mappable in [*axes.images, *axes.collections]:
        label = mappable.get_label()
        if label == '_nolegend_' or mappable.get_array() is None:
            continue
        labeled_mappables.append((label, mappable))
    mappables = []
    cmaps = [(cmap, name) for name, cmap in sorted(cm._colormaps.items())]
    for label, mappable in labeled_mappables:
        cmap = mappable.get_cmap()
        if cmap.name not in cm._colormaps:
            cmaps = [(cmap, cmap.name), *cmaps]
        low, high = mappable.get_clim()
        mappabledata = [
            ('Label', label),
            ('Colormap', [cmap.name] + cmaps),
            ('Min. value', low),
            ('Max. value', high),
        ]
        if hasattr(mappable, "get_interpolation"):  # Images.
            interpolations = [
                (name, name) for name in sorted(mimage.interpolations_names)]
            mappabledata.append((
                'Interpolation',
                [mappable.get_interpolation(), *interpolations]))

            interpolation_stages = ['data', 'rgba', 'auto']
            mappabledata.append((
                'Interpolation stage',
                [mappable.get_interpolation_stage(), *interpolation_stages]))

        mappables.append([mappabledata, label, ""])
    # Is there a scalarmappable displayed?
    has_sm = bool(mappables)

    datalist = []
    if curves:
        datalist.append((curves, "Curves", ""))
    if mappables:
        datalist.append((mappables, "Images, etc.", ""))

    if not datalist:
        # 편집할 라인도 이미지도 없으면(예: 그래프를 그리기 전) 열어도 빈 다이얼로그일
        # 뿐이니 아예 열지 않는다.
        return

    def apply_callback(data):
        """A callback to apply changes."""
        curves = data.pop(0) if has_curve else []
        mappables = data.pop(0) if has_sm else []
        if data:
            raise ValueError("Unexpected field")

        # Set / Curves
        for index, curve in enumerate(curves):
            line = labeled_lines[index][1]
            (label, linestyle, drawstyle, linewidth, color, marker, markersize,
             markerfacecolor, markeredgecolor) = curve
            line.set_label(label)
            line.set_linestyle(linestyle)
            line.set_drawstyle(drawstyle)
            line.set_linewidth(linewidth)
            rgba = mcolors.to_rgba(color)
            line.set_alpha(None)
            line.set_color(rgba)
            # 이 앱은 Y축마다(twinx로 만든 축 포함) 선을 하나씩만 그리므로, 그 축의
            # y라벨/눈금 색을 선 색과 항상 맞춰둔다(plot_lines()가 처음 그릴 때의 규칙과
            # 동일). 여기서 안 맞춰주면 Customize에서 라인 색만 바뀌고 축 색은 예전 색
            # 그대로 남아 서로 어긋나 보인다.
            line_axes = line.axes
            line_axes.yaxis.label.set_color(rgba)
            line_axes.tick_params(axis="y", colors=rgba)
            if marker != 'none':
                line.set_marker(marker)
                line.set_markersize(markersize)
                line.set_markerfacecolor(markerfacecolor)
                line.set_markeredgecolor(markeredgecolor)

        # Set ScalarMappables.
        for index, mappable_settings in enumerate(mappables):
            mappable = labeled_mappables[index][1]
            if len(mappable_settings) == 6:
                label, cmap, low, high, interpolation, interpolation_stage = \
                  mappable_settings
                mappable.set_interpolation(interpolation)
                mappable.set_interpolation_stage(interpolation_stage)
            elif len(mappable_settings) == 4:
                label, cmap, low, high = mappable_settings
            mappable.set_label(label)
            mappable.set_cmap(cmap)
            mappable.set_clim(*sorted([low, high]))

        if on_apply is not None:
            on_apply()

        # Redraw
        figure = axes.get_figure()
        figure.canvas.draw()

    _formlayout.fedit(
        datalist, title="Figure options", parent=parent,
        icon=QtGui.QIcon(
            str(cbook._get_data_path('images', 'qt4_editor_options.svg'))),
        apply=apply_callback)


def axis_edit(axis, parent=None, on_apply=None):
    """축(X 또는 Y)을 더블클릭했을 때 그 축 하나의 Min/Max/Label만 편집하는 작은 다이얼로그.

    `figure_edit`(Customize 버튼)은 axes 전체(모든 축 + 곡선 스타일)를 한 번에 다루는
    큰 다이얼로그라, 축 범위 하나만 빠르게 바꾸고 싶을 때 쓰기엔 번거롭다. 여기서는
    `figure_edit`에서 축 하나 분량의 Min/Max/Label 로직만 떼어냈다.

    on_apply: OK/Apply 직후 호출되는 콜백(인자 없음). 이 앱에서는 범례 갱신
    (`PlotCanvas.refresh_legend`)을 넘겨받는다 — Y축이면 아래에서 라벨을 그 축의
    선(legend label)에도 맞춰준 뒤, 이 콜백으로 범례에 반영한다.
    """
    axes = axis.axes
    name = "x" if axis is axes.xaxis else "y"
    converter = axis.get_converter()
    units = axis.get_units()

    if isinstance(converter, DateConverter):
        lim = list(map(num2date, getattr(axes, f"get_{name}lim")()))
    else:
        lim = list(map(float, getattr(axes, f"get_{name}lim")()))

    datalist = [
        ('Min', lim[0]),
        ('Max', lim[1]),
        ('Label', axis.label.get_text()),
    ]

    def apply_callback(data):
        axis_min, axis_max, axis_label = data
        orig_limits = getattr(axes, f"get_{name}lim")()

        axis._set_lim(axis_min, axis_max, auto=False)
        axis.set_label_text(axis_label)
        # Restore the unit data (그대로 두면 _set_lim이 초기화될 수 있음 — figure_edit과 동일)
        axis._set_converter(converter)
        axis.set_units(units)

        if name == "y":
            # 이 앱은 Y축마다 선을 하나씩만 그려서, Y축 라벨과 그 선의 범례 이름은 원래
            # 같은 값(Y 컬럼명)이다. 축 라벨만 바꾸고 선의 label을 그대로 두면 범례가
            # 예전 이름으로 남아 서로 어긋나 보이므로 같이 바꿔준다.
            lines = axes.get_lines()
            if lines:
                lines[0].set_label(axis_label)

        if on_apply is not None:
            on_apply()

        figure = axes.get_figure()
        figure.canvas.draw()
        if getattr(axes, f"get_{name}lim")() != orig_limits:
            toolbar = figure.canvas.toolbar
            if toolbar is not None:
                toolbar.push_current()

    _formlayout.fedit(
        datalist, title=f"{'X' if name == 'x' else 'Y'}축 편집 — {axis.label.get_text()}",
        parent=parent, apply=apply_callback)
