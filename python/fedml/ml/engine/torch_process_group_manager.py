import logging
import os

import torch
import torch.distributed as dist


class TorchProcessGroupManager:
    def __init__(self, rank, world_size, master_address, master_port, only_gpu):
        """
        Initialize the TorchProcessGroupManager.

        Args:
            rank (int): The rank of the current process.
            world_size (int): The total number of processes in the distributed training.
            master_address (str): The address of the master process for communication.
            master_port (int): The port for communication with the master process.
            only_gpu (bool): Flag indicating whether only GPUs are used for communication.

        Initializes the process group and creates a messaging process group for communication.
        """
        logging.info("Start process group")
        logging.info(
            "rank: %d, world_size: %d, master_address: %s, master_port: %s"
            % (rank, world_size, master_address, master_port)
        )
        os.environ["MASTER_ADDR"] = master_address
        os.environ["MASTER_PORT"] = str(master_port)
        os.environ["WORLD_SIZE"] = str(world_size)
        os.environ["RANK"] = str(rank)

        env_dict = {
            key: os.environ[key]
            for key in ("MASTER_ADDR", "MASTER_PORT", "RANK", "WORLD_SIZE",)
        }
        logging.info(f"[{os.getpid()}] Initializing process group with: {env_dict}")

        backend = (
            dist.Backend.NCCL
            if (only_gpu and torch.cuda.is_available())
            else dist.Backend.GLOO
        )
        logging.info(f"Process group backend: {backend}")

        # initialize the process group
        dist.init_process_group(backend=backend)

        self.messaging_pg = dist.new_group(backend=backend)

        logging.info("Initiated")

    def cleanup(self):
        """
        Clean up the process group.

        Destroys the process group and performs cleanup.
        """
        dist.destroy_process_group()

    def get_process_group(self):
        """
        Get the messaging process group.

        Returns:
            torch.distributed.ProcessGroup: The messaging process group for communication.
        """
        return self.messaging_pg
