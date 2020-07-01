#!/usr/bin/env python
"""
Main module for EsmEnvironment.
"""

import os
import warnings

import esm_parser
from esm_rcfile import FUNCTION_PATH

######################################################################################
########################### class "environment_infos" ################################
######################################################################################


class EnvironmentInfos:
    def __init__(self, run_or_compile, complete_config=None):

        if not complete_config:
            # should not happen anymore
            self.machine_file = esm_parser.determine_computer_from_hostname()
            self.config = esm_parser.yaml_file_to_dict(self.machine_file)
            esm_parser.basic_choose_blocks(self.config, self.config)
            esm_parser.recursive_run_function(
                [],
                self.config,
                "atomic",
                esm_parser.find_variable,
                self.config,
                [],
                True,
            )
        else:
            self.config = complete_config["computer"]

        # PG: Why?
        for entry in ["add_module_actions", "add_export_vars"]:
            if entry in self.config:
                del self.config[entry]

        self.apply_config_changes(run_or_compile, complete_config)
        self.add_esm_var()
        self.commands = self.get_shell_commands()

    def add_esm_var(self):
        """Adds the ENVIRONMENT_SET_BY_ESMTOOLS=TRUE to the config, for later
        dumping to the shell script."""
        if "export_vars" in self.config:
            self.config["export_vars"] += ["ENVIRONMENT_SET_BY_ESMTOOLS=TRUE"]
        else:
            self.config["export_vars"] = ["ENVIRONMENT_SET_BY_ESMTOOLS=TRUE"]

    def apply_config_changes(self, run_or_compile, config):
        for model in config:
            self.apply_model_changes(
                model, run_or_compile=run_or_compile, modelconfig=config[model]
            )

    def apply_model_changes(self, model, run_or_compile="runtime", modelconfig=None):
        try:
            if not modelconfig:
                # should not happen anymore...
                modelconfig = esm_parser.yaml_file_to_dict(
                    FUNCTION_PATH + "/" + model + "/" + model
                )
            thesechanges = run_or_compile + "_environment_changes"
            if thesechanges in modelconfig:
                if "environment_changes" in modelconfig:
                    modelconfig["environment_changes"].update(modelconfig[thesechanges])
                else:
                    modelconfig["environment_changes"] = modelconfig[thesechanges]

            if "environment_changes" in modelconfig:
                for entry in ["add_module_actions", "add_export_vars"]:
                    if not entry in self.config:
                        self.config[entry] = []
                    if entry in modelconfig["environment_changes"]:
                        if isinstance(modelconfig["environment_changes"][entry], list):
                            self.config[entry] += modelconfig["environment_changes"][
                                entry
                            ]
                        else:
                            self.config[entry] += [
                                modelconfig["environment_changes"][entry]
                            ]
                        del modelconfig["environment_changes"][entry]

                self.config.update(modelconfig["environment_changes"])
                all_keys = self.config.keys()
                for key in all_keys:
                    if "choose_computer." in key:
                        newkey = key.replace("computer.", "")
                        self.config[newkey] = self.config[key]
                        del self.config[key]

                esm_parser.basic_choose_blocks(self.config, self.config)

                for entry in ["add_module_actions", "add_export_vars"]:
                    if entry in self.config:
                        del self.config[entry]
        except:
            pass

    def replace_model_dir(self, model_dir):
        """
        Replaces any instances of ${model_dir} in the config section
        "export_vars" with the argument

        Parameters
        ----------
        model_dir : str
            The replacement string for ${model_dir}
        """
        for entry in ["export_vars"]:
            if entry in self.config:
                newlist = []
                for line in self.config[entry]:
                    newline = line.replace("${model_dir}", model_dir)
                    newlist.append(newline)
                self.config[entry] = newlist

    def get_shell_commands(self):
        """
        Gathers module actions and export variables from the config to a list,
        prepending appropriate shell command words (e.g. module and export)

        Returns
        -------
        list
        """
        environment = []
        if "module_actions" in self.config:
            for action in self.config["module_actions"]:
                environment.append("module " + action)
        # Add an empty string as a newline:
        environment.append("")
        if "export_vars" in self.config:
            for var in self.config["export_vars"]:
                if isinstance(var, dict):
                    key = list(var.keys())[0]
                    value = var[key]
                    environment.append("export " + key + "='" + str(value) + "'")
                else:
                    environment.append("export " + str(var))
        return environment

    def write_dummy_script(self, include_set_e=True):
        """
        Writes a dummy script containing only the header information, module
        commands, and export variables. The actual compile/configure commands
        are added later.

        Parameters
        ----------
        include_set_e : bool
            Default to True, whether or not to include a ``set -e`` at the
            beginning of the script. This causes the shell to stop as soon as
            an error is encountered.
        """
        with open("dummy_script.sh", "w") as script_file:
            script_file.write(
                "# Dummy script generated by esm-tools, to be removed later: \n"
            )
            if include_set_e:
                script_file.write("set -e\n")
            for command in self.commands:
                script_file.write(command + "\n")
            script_file.write("\n")

    @staticmethod
    def cleanup_dummy_script():
        """Removes the ``dummy_script.sh`` if it exists."""
        try:
            os.remove("dummy_script.sh")
        except OSError:
            print("No file dummy_script.sh there; nothing to do...")

    @staticmethod
    def add_commands(commands, name):
        """
        Writes all commands in a list to a file named ``<name>_script.sh``,
        located in the current working directory. The header from this script
        is read from ``dummy_script.sh``, also in the current working
        directory.

        Parameters
        ----------
        commands : list of str
            List of the commands to write to the file after the header
        name : str
            Name of the script, generally something like ``comp_echam-6.3.05``

        Returns
        -------
        str :
            ``name`` + "_script.sh"
        """
        if commands:
            with open(name + "_script.sh", "w") as newfile:
                with open("dummy_script.sh", "r") as dummy_file:
                    newfile.write(dummy_file.read())
                for command in commands:
                    newfile.write(command + "\n")
        return name + "_script.sh"

    def output(self):
        esm_parser.pprint_config(self.config)


class environment_infos(EnvironmentInfos):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Please change your code to use EnvironmentInfos!",
            DeprecationWarning,
            stacklevel=2,
        )
        super(environment_infos, self).__init__(*args, **kwargs)
