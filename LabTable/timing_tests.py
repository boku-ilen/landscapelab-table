import timeit

import cv2
import time

from LabTable.Model.ProgramStage import ProgramStage
from LabTable.TableOutputStream import TableOutputStream, TableOutputChannel
from LabTable.__main__ import LabTable

if __name__ != "__main__":
    exit(1)

def run_timing_test(function, runs, label):
    # JIT warmup

    for i in range(10):
        function()

    run_time = timeit.timeit(function, number=runs, timer=time.perf_counter_ns)
    print(f"{label} took {(run_time / runs) / 1000000}ms on average")

def main_loop_mock(color_image):
    table.output_stream.update(table.program_stage)
    # Add some additional information to the debug window
    #color_image_debug = color_image.copy()

    # always write the current frame to the board detection channel
    table.output_stream.write_to_channel(TableOutputChannel.CHANNEL_BOARD_DETECTION, color_image)

    # normal brick detection, then switch to capture if requested
    table.pre_drawing_stage = table.program_stage.current_stage
    table.do_brick_detection(color_image)

table = LabTable()
while table.program_stage.current_stage == ProgramStage.FIND_CORNERS:
    setup_round_time = timeit.timeit(lambda: table.run(once=True), number=1)
    print(setup_round_time)

captured_img = table.input_stream.get_frame()[1]

cv2.imshow("capture base", captured_img)
run_timing_test(
    lambda: table.board_detector.rectify(captured_img),
    1000,
    "normal image rectification"
)

rectified = table.board_detector.rectify(captured_img)
run_timing_test(
    lambda: table.shape_detector.detect_contours(rectified),
    1000,
    "Shape detector: contour detection"
)

upscaled = cv2.resize(captured_img, (2160,3840))

run_timing_test(
    lambda: table.board_detector.rectify(upscaled),
    1000,
    "4k image rectification"
)
upscaled_u = cv2.UMat(upscaled)
run_timing_test(
    lambda: table.board_detector.rectify(upscaled_u),
    1000,
    "4k compute image rectification"
)


rectified_4k = table.board_detector.rectify(upscaled)
run_timing_test(
    lambda: table.shape_detector.detect_contours(rectified_4k),
    1000,
    "Shape detector: 4k contour detection"
)

contours = table.shape_detector.detect_contours(rectified)

run_timing_test(
    lambda: list(table.shape_detector.detect_brick(contour, rectified) for contour in contours),
    1000,
    "brick detection on all contours"
)

rectified_dbg = rectified.copy()

run_timing_test(
    lambda: (TableOutputStream.mark_candidates(rectified_dbg, contour) for contour in contours),
    1000,
    "candidate marking"
)

run_timing_test(
    lambda: main_loop_mock(captured_img),
    100,
    "main loop mock"
)

run_timing_test(
    lambda: main_loop_mock(upscaled),
    100,
    "main loop mock 4k"
)
run_timing_test(
    lambda: table.output_stream.update(table.program_stage),
    100,
    "outputstream update"
)
cv2.waitKey(-1)
table.output_stream.close()
table.input_stream.close()