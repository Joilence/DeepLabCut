import os
import deeplabcut
import numpy as np
import pandas as pd
from deeplabcut.utils import auxfun_multianimal, auxiliaryfunctions


if __name__ == "__main__":
    TASK = "multi_mouse"
    SCORER = "dlc_team"
    NUM_FRAMES = 5
    TRAIN_SIZE = 0.8
    NET = "dlcrnet_ms5"
    # NET = "efficientnet-b0"
    N_ITER = 5

    basepath = os.path.dirname(os.path.realpath(__file__))
    video = "m3v1mp4"
    video_path = os.path.join(
        basepath, "openfield-Pranav-2018-10-30", "videos", video + ".mp4"
    )

    print("Creating project...")
    config_path = deeplabcut.create_new_project(
        TASK, SCORER, [video_path], copy_videos=True, multianimal=True
    )
    print("Project created.")

    print("Editing config...")
    cfg = auxiliaryfunctions.edit_config(
        config_path, {"numframes2pick": NUM_FRAMES, "TrainingFraction": [TRAIN_SIZE]}
    )
    print("Config edited.")

    print("Extracting frames...")
    deeplabcut.extract_frames(config_path, mode="automatic", userfeedback=False)
    print("Frames extracted.")

    print("Creating artificial data...")
    rel_folder = os.path.join("labeled-data", os.path.splitext(video)[0])
    image_folder = os.path.join(cfg["project_path"], rel_folder)
    n_animals = len(cfg["individuals"])
    (
        animals,
        bodyparts_single,
        bodyparts_multi,
    ) = auxfun_multianimal.extractindividualsandbodyparts(cfg)
    animals_id = [i for i in range(n_animals) for _ in bodyparts_multi] + [
        n_animals
    ] * len(bodyparts_single)
    map_ = dict(zip(range(len(animals)), animals))
    individuals = [map_[ind] for ind in animals_id for _ in range(2)]
    scorer = [SCORER] * len(individuals)
    coords = ["x", "y"] * len(animals_id)
    bodyparts = [
        bp for _ in range(n_animals) for bp in bodyparts_multi for _ in range(2)
    ]
    bodyparts += [bp for bp in bodyparts_single for _ in range(2)]
    columns = pd.MultiIndex.from_arrays(
        [scorer, individuals, bodyparts, coords],
        names=["scorer", "individuals", "bodyparts", "coords"],
    )
    index = [
        os.path.join(rel_folder, image)
        for image in auxiliaryfunctions.grab_files_in_folder(image_folder, "png")
    ]
    fake_data = np.tile(
        np.repeat(50 * np.arange(len(animals_id)) + 100, 2), (len(index), 1)
    )
    df = pd.DataFrame(fake_data, index=index, columns=columns)
    output_path = os.path.join(image_folder, f"CollectedData_{SCORER}.csv")
    df.to_csv(output_path)
    df.to_hdf(
        output_path.replace("csv", "h5"), "df_with_missing", format="table", mode="w"
    )
    print("Artificial data created.")

    print("Cropping and exchanging")
    deeplabcut.cropimagesandlabels(config_path, userfeedback=False)

    print("Checking labels...")
    deeplabcut.check_labels(config_path, draw_skeleton=False)
    print("Labels checked.")

    print("Creating train dataset...")
    deeplabcut.create_multianimaltraining_dataset(config_path, net_type=NET)
    print("Train dataset created.")

    print("Editing pose config...")
    model_folder = auxiliaryfunctions.GetModelFolder(
        TRAIN_SIZE, 1, cfg, cfg["project_path"]
    )
    pose_config_path = os.path.join(model_folder, "train/pose_cfg.yaml")
    edits = {
        "global_scale": 0.5,
        "batch_size": 1,
        "save_iters": N_ITER,
        "display_iters": N_ITER // 2,
        # "multi_step": [[0.001, N_ITER]],
    }
    deeplabcut.auxiliaryfunctions.edit_config(pose_config_path, edits)
    print("Pose config edited.")

    print("Training network...")
    deeplabcut.train_network(config_path, maxiters=N_ITER)
    print("Network trained.")

    print("Evaluating network...")
    deeplabcut.evaluate_network(config_path, plotting=True)

    print("Network evaluated....")

    print("Extracting maps...")
    deeplabcut.extract_save_all_maps(config_path, Indices=[0, 1, 2])

    new_video_path = deeplabcut.ShortenVideo(
        video_path,
        start="00:00:00",
        stop="00:00:01",
        outsuffix="short",
        outpath=os.path.join(cfg["project_path"], "videos"),
    )

    print("Analyzing video...")
    deeplabcut.analyze_videos(config_path, [new_video_path], "mp4", robust_nframes=True,allow_growth=True)
    
    print("Video analyzed.")

    print("Create video with all detections...")
    scorer, _ = auxiliaryfunctions.GetScorerName(cfg, 1, TRAIN_SIZE)
    deeplabcut.create_video_with_all_detections(
        config_path, [new_video_path], shuffle=1, displayedbodyparts=["bodypart1"]
    )
    print("Video created.")

    print("Convert detections to tracklets...")
    deeplabcut.convert_detections2tracklets(
        config_path, [new_video_path], "mp4", track_method="box"
    )
    deeplabcut.convert_detections2tracklets(
        config_path, [new_video_path], "mp4", track_method="ellipse"
    )
    print("Tracklets created...")

    pickle_file = os.path.join(
        os.path.dirname(basepath), "tests", "data", "trimouse_tracklets.pickle"
    )
    deeplabcut.stitch_tracklets(
        config_path,
        pickle_file,
        output_name=os.path.splitext(new_video_path)[0] + scorer + "_el.h5",
    )

    print("Plotting trajectories...")
    deeplabcut.plot_trajectories(
        config_path, [new_video_path], "mp4", track_method="ellipse"
    )
    print("Trajectory plotted.")

    print("Creating labeled video...")
    deeplabcut.create_labeled_video(
        config_path,
        [new_video_path],
        "mp4",
        save_frames=False,
        color_by="individual",
        track_method="ellipse",
    )
    print("Labeled video created.")

    print("Filtering predictions...")
    deeplabcut.filterpredictions(
        config_path, [new_video_path], "mp4", track_method="ellipse"
    )
    print("Predictions filtered.")
    """
    print("Extracting outlier frames...")
    deeplabcut.extract_outlier_frames(
        config_path, [new_video_path], "mp4", automatic=True, track_method="ellipse"
    )
    print("Outlier frames extracted.")
    """
    print("ALL DONE!!! - default multianimal cases are functional.")
