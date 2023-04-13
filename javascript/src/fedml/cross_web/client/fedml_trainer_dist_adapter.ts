/* eslint-disable @typescript-eslint/no-unused-vars */
import { FedMLTrainer } from './fedml_trainer'
import { ModelTrainerCLS } from './ModelTrainerCls'

export class TrainerDistAdapter {
  device: string
  client_rank
  model: any
  trainData: any
  trainDataLabel: any
  testData: any
  testDataLabel: any
  model_trainer
  client_index
  trainer
  args: Object

  constructor(
    args: Object,
    device: string,
    client_rank: any,
    model: any,
    trainData: any,
    trainDataLabel: any,
    testData: any,
    testDataLabel: any,
    model_trainer = null,
  ) {
    if (model_trainer == null) {
      this.model_trainer = this.create_model_trainer(
        model,
        trainData,
        trainDataLabel,
        testData,
        testDataLabel,
        args,
      )
    }
    this.trainData = trainData
    this.trainDataLabel = trainDataLabel
    this.testData = testData
    this.testDataLabel = testDataLabel
    const client_index = this.client_rank - 1
    this.model_trainer!.set_id(client_index)
    console.log('Initializing Trainer')
    const trainer = this.get_trainer(
      client_index,
      trainData,
      trainDataLabel,
      testData,
      testDataLabel,
      device,
      args,
      this.model_trainer,
    )

    this.client_index = client_index
    this.client_rank = client_rank
    this.device = device
    this.trainer = trainer
    this.args = args
  }

  /**
   * @description: get trainer
   */
  get_trainer(
    client_index: number,
    trainData: any,
    trainDataLabel: any,
    testData: any,
    testDataLabel: any,
    device: any,
    args: any,
    model_trainer: ModelTrainerCLS | undefined,
  ) {
    return new FedMLTrainer(
      client_index,
      trainData,
      trainDataLabel,
      testData,
      testDataLabel,
      device,
      args,
      model_trainer,
    )
  }

  async train(round_idx: number | null | undefined) {
    if (!round_idx)
      return

    const weights = await this.trainer.train(round_idx)
    return {
      weights,
    }
  }

  update_model(model_params: any) {
    this.trainer.update_model(model_params)
  }

  update_dataset(client_index: number) {
    const _client_index = client_index || this.client_index
  }

  create_model_trainer(model: any, trainData: any, trainDataLabel: any, testData: any, testDataLabel: any, args: any) {
    const model_trainer = new ModelTrainerCLS(
      model,
      trainData,
      trainDataLabel,
      testData,
      testDataLabel,
      args,
    )
    return model_trainer
  }
}